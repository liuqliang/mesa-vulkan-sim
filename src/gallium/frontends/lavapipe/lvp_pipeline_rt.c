#include "nir/nir.h"
#include "lvp_pipeline.h"
#include "lvp_private.h"
#include "vk_pipeline.h"
#include "vk_pipeline_cache.h"

#include "gpgpusim_calls_from_mesa.h"

#include <stdlib.h>
#include <string.h>

struct vsim_pipeline_stage {
   gl_shader_stage stage;
   const VkPipelineShaderStageCreateInfo *info;
   nir_shader *nir;
   const char *entrypoint;
   struct anv_shader_bin *bin;
   const VkSpecializationInfo *spec_info;
};

#define VSIM_KHR_CONTINUATION_STACK_DEFAULT_BYTES 4096u
#define VSIM_KHR_CONTINUATION_STACK_MAX_BYTES (1u << 20)
#define VSIM_KHR_CALLABLE_DEPTH_CAPACITY 8u

static bool
vsim_khr_continuation_stack_capacity(uint32_t *capacity_out)
{
   const char *text = getenv("VULKAN_SIM_RTCORE_CONTINUATION_STACK_BYTES");
   if (!text || !text[0]) {
      *capacity_out = VSIM_KHR_CONTINUATION_STACK_DEFAULT_BYTES;
      return true;
   }
   char *end = NULL;
   unsigned long value = strtoul(text, &end, 10);
   if (!end || end == text || *end != '\0' || value == 0 ||
       (value & 7u) != 0 || value > VSIM_KHR_CONTINUATION_STACK_MAX_BYTES) {
      return false;
   }
   *capacity_out = (uint32_t)value;
   return true;
}

static bool
vsim_validate_compiled_continuation_stack(
   const VkRayTracingPipelineCreateInfoKHR *info,
   char shader_paths[20][200])
{
   const char *candidate =
      getenv("VULKAN_SIM_RTCORE_MEGAKERNEL_CONTINUATION_STACK");
   if (!candidate || strcmp(candidate, "1"))
      return true;

   uint32_t capacity = 0;
   if (!vsim_khr_continuation_stack_capacity(&capacity)) {
      fprintf(stderr,
              "LVP: invalid VULKAN_SIM_RTCORE_CONTINUATION_STACK_BYTES; "
              "expected an 8-byte-aligned integer in [8, 1048576]\n");
      return false;
   }

   uint32_t max_trace_frame = 0;
   uint32_t max_callable_frame = 0;
   uint32_t max_report_frame = 0;
   for (uint32_t index = 0; index < info->stageCount; ++index) {
      if (!shader_paths[index][0])
         continue;
      FILE *file = fopen(shader_paths[index], "r");
      if (!file) {
         fprintf(stderr,
                 "LVP: cannot inspect compiled continuation profile %s\n",
                 shader_paths[index]);
         return false;
      }
      char line[1024];
      while (fgets(line, sizeof(line), file)) {
         char *marker = strstr(line, "rtcore_continuation_push site=");
         if (!marker)
            continue;
         unsigned site = 0;
         unsigned frame_bytes = 0;
         char kind[16] = {0};
         if (sscanf(marker,
                    "rtcore_continuation_push site=%u kind=%15s "
                    "frame_bytes=%u",
                    &site, kind, &frame_bytes) != 3 ||
             frame_bytes < 32 || (frame_bytes & 7u) != 0) {
            fclose(file);
            fprintf(stderr,
                    "LVP: malformed compiled continuation frame marker\n");
            return false;
         }
         if (!strcmp(kind, "trace"))
            max_trace_frame = MAX2(max_trace_frame, frame_bytes);
         else if (!strcmp(kind, "callable"))
            max_callable_frame = MAX2(max_callable_frame, frame_bytes);
         else if (!strcmp(kind, "report"))
            max_report_frame = MAX2(max_report_frame, frame_bytes);
         else {
            fclose(file);
            fprintf(stderr,
                    "LVP: unknown compiled continuation frame kind %s\n",
                    kind);
            return false;
         }
      }
      fclose(file);
   }

   const uint64_t required =
      (uint64_t)info->maxPipelineRayRecursionDepth * max_trace_frame +
      (uint64_t)VSIM_KHR_CALLABLE_DEPTH_CAPACITY * max_callable_frame +
      max_report_frame;
   if (required > capacity) {
      fprintf(stderr,
              "LVP: RTCORE_KHR_PIPELINE_STACK_CONFIG required_bytes=%llu "
              "capacity_bytes=%u trace_frame_bytes=%u trace_depth=%u "
              "callable_frame_bytes=%u callable_depth=%u "
              "report_frame_bytes=%u validated=0 "
              "reason=aggregate_capacity_exceeded_before_execution\n",
              (unsigned long long)required, capacity, max_trace_frame,
              info->maxPipelineRayRecursionDepth, max_callable_frame,
              VSIM_KHR_CALLABLE_DEPTH_CAPACITY, max_report_frame);
      fprintf(stderr,
              "LVP: resident continuation pipeline requires %llu bytes "
              "but configured per-lane capacity is %u bytes "
              "(trace_frame=%u trace_depth=%u callable_frame=%u "
              "callable_depth=%u report_frame=%u)\n",
              (unsigned long long)required, capacity, max_trace_frame,
              info->maxPipelineRayRecursionDepth, max_callable_frame,
              VSIM_KHR_CALLABLE_DEPTH_CAPACITY, max_report_frame);
      return false;
   }
   printf("LVP: RTCORE_KHR_PIPELINE_STACK_CONFIG required_bytes=%llu "
          "capacity_bytes=%u trace_frame_bytes=%u trace_depth=%u "
          "callable_frame_bytes=%u callable_depth=%u "
          "report_frame_bytes=%u validated=1\n",
          (unsigned long long)required, capacity, max_trace_frame,
          info->maxPipelineRayRecursionDepth, max_callable_frame,
          VSIM_KHR_CALLABLE_DEPTH_CAPACITY, max_report_frame);
   return true;
}


static bool gpgpusim_initialized = false;
static int shader_ID = 0;

static VkResult
vsim_validate_ray_tracing_pipeline_capabilities(
   struct lvp_device *device,
   const VkRayTracingPipelineCreateInfoKHR *info)
{
   const char *continuation_candidate =
      getenv("VULKAN_SIM_RTCORE_MEGAKERNEL_CONTINUATION_STACK");
   uint32_t continuation_capacity = 0;
   if (continuation_candidate && !strcmp(continuation_candidate, "1") &&
       (!vsim_khr_continuation_stack_capacity(&continuation_capacity) ||
        info->stageCount > 20)) {
      fprintf(stderr,
              "LVP: invalid resident continuation capacity or stage count "
              "(stageCount=%u)\n",
              info->stageCount);
      return vk_error(device, VK_ERROR_FEATURE_NOT_PRESENT);
   }
   if (continuation_candidate && !strcmp(continuation_candidate, "1") &&
       (info->maxPipelineRayRecursionDepth == 0 ||
        info->maxPipelineRayRecursionDepth > 8)) {
      fprintf(stderr,
              "LVP: resident continuation pipeline recursion depth %u is "
              "outside the supported range [1, 8]\n",
              info->maxPipelineRayRecursionDepth);
      return vk_error(device, VK_ERROR_FEATURE_NOT_PRESENT);
   }

   for (uint32_t i = 0; i < info->stageCount; i++) {
      if (info->pStages[i].stage == VK_SHADER_STAGE_CALLABLE_BIT_KHR &&
          (!continuation_candidate || strcmp(continuation_candidate, "1"))) {
         fprintf(stderr,
                 "LVP: callable shader execution requires the default-off "
                 "resident continuation candidate\n");
         return vk_error(device, VK_ERROR_FEATURE_NOT_PRESENT);
      }
   }

   for (uint32_t i = 0; i < info->groupCount; i++) {
      const VkRayTracingShaderGroupCreateInfoKHR *group = &info->pGroups[i];
      if (group->type ==
             VK_RAY_TRACING_SHADER_GROUP_TYPE_PROCEDURAL_HIT_GROUP_KHR &&
          group->anyHitShader != VK_SHADER_UNUSED_KHR &&
          (!continuation_candidate || strcmp(continuation_candidate, "1"))) {
         fprintf(stderr,
                 "LVP: procedural intersection plus any-hit is unsupported "
                 "without the resident continuation candidate\n");
         return vk_error(device, VK_ERROR_FEATURE_NOT_PRESENT);
      }
   }

   return VK_SUCCESS;
}

static void translate_nir_to_ptx(nir_shader *shader, char* shaderPath)
{
   FILE *pFile;
   char *mesa_root = getenv("MESA_ROOT");
   char *filePath = "gpgpusimShaders/";
   char fileName[50];
   char *label; // in case there are multiple variants of the same shader
   char *extension = ".ptx";
   
   label = shader->info.label;
   if (!label){
      label = "0";
   }

   switch (shader->info.stage) {
      case MESA_SHADER_RAYGEN:
         strcpy(fileName, "MESA_SHADER_RAYGEN");
         break;
      case MESA_SHADER_ANY_HIT:
         strcpy(fileName, "MESA_SHADER_ANY_HIT");
         break;
      case MESA_SHADER_CLOSEST_HIT:
         strcpy(fileName, "MESA_SHADER_CLOSEST_HIT");
         break;
      case MESA_SHADER_MISS:
         strcpy(fileName, "MESA_SHADER_MISS");
         break;
      case MESA_SHADER_INTERSECTION:
         strcpy(fileName, "MESA_SHADER_INTERSECTION");
         break;
      case MESA_SHADER_CALLABLE:
         strcpy(fileName, "MESA_SHADER_CALLABLE");
         break;
      default:
         unreachable("Invalid shader type");
   }

   char fullPath[200];
   snprintf(fullPath, sizeof(fullPath), "%s%s%s_%d%s", mesa_root, filePath, fileName, shader_ID++, extension);
   
   char command[200];

   if(!gpgpusim_initialized){
      snprintf(command, sizeof(command), "rm -rf %s%s", mesa_root, filePath);
      system(command);
      gpgpusim_initialized = true;
   }

   snprintf(command, sizeof(command), "mkdir -p %s%s", mesa_root, filePath);
   system(command);
   
   pFile = fopen (fullPath , "w");
   printf("GPGPU-SIM VULKAN: Translating NIR %s to PTX\n", fileName);
   nir_translate_shader_to_ptx(shader, pFile, fullPath);

   strcpy(shaderPath, fullPath);
}

static void run_rt_translation_passes()
{
   char *mesa_root = getenv("MESA_ROOT");
   char *filePath = "gpgpusimShaders/";

   char command[400];
   snprintf(command, sizeof(command), "python3 %s/src/compiler/ptx/ptx_lower_instructions.py %s%s", mesa_root, mesa_root, filePath);
   int result = system(command);

   if (result != 0)
   {
      printf("MESA: ERROR ** while translating nir to PTX %d\n", result);
      exit(1);
   }
}

static nir_shader *
vsim_pipeline_stage_get_nir(
   struct lvp_pipeline *pipeline,
   const VkPipelineShaderStageCreateInfo *sinfo)
{
   nir_shader *nir;

   nir = vsim_shader_spirv_to_nir(pipeline, sinfo);
   if (nir) {
      return nir;
   }

   return NULL;
}

static VkResult
vsim_compile_ray_tracing_pipeline(
   struct lvp_pipeline *pipeline,
   const VkRayTracingPipelineCreateInfoKHR *info)
{
   printf("LVP: Compiling ray tracing pipeline...\n");
   VkResult result = VK_SUCCESS;
   LVP_FROM_HANDLE(lvp_pipeline_layout, layout, info->layout);

   void *pipeline_ctx = ralloc_context(NULL);
   struct vsim_pipeline_stage *stages =
      rzalloc_array(pipeline_ctx, struct vsim_pipeline_stage, info->stageCount);

   char shaderPaths[20][200] = {{0}};
   for (uint32_t i = 0; i < info->stageCount; i++) {
      printf("LVP: Compiling shader stage %d\n", i);
      const VkPipelineShaderStageCreateInfo *sinfo = &info->pStages[i];
      if (sinfo->module == VK_NULL_HANDLE)
         continue;

      stages[i] = (struct vsim_pipeline_stage) {
         .stage = vk_to_mesa_shader_stage(sinfo->stage),
         .entrypoint = sinfo->pName,
         .spec_info = sinfo->pSpecializationInfo,
      };

      stages[i].nir = vsim_pipeline_stage_get_nir(pipeline, sinfo);

      if (stages[i].nir == NULL) {
         printf("LVP: NIR missing\n");
         ralloc_free(pipeline_ctx);
         return VK_ERROR_OUT_OF_HOST_MEMORY;
      }

      // Insert NIR to PTX translator here for each different ray tracing shaders, the lowered shaders under have too many intel specific intrinsics
      if(stages[i].stage >= MESA_SHADER_RAYGEN && stages[i].stage <= MESA_SHADER_CALLABLE) { // shader type from 8 to 13
         printf("LVP: Translating shader %d (type %d)\n", i, stages[i].stage);
         translate_nir_to_ptx(stages[i].nir, shaderPaths[i]);
      }
      pipeline->shaders[i].pipeline_nir = ralloc(NULL, struct lvp_pipeline_nir);
      pipeline->shaders[i].pipeline_nir->nir = stages[i].nir;
      pipeline->shaders[i].pipeline_nir->ref_cnt = 1;
   }

   // Vulkan-Sim additions
   printf("LVP: run_rt_translation_passes\n");
   run_rt_translation_passes();

   if (!vsim_validate_compiled_continuation_stack(info, shaderPaths)) {
      ralloc_free(pipeline_ctx);
      return VK_ERROR_FEATURE_NOT_PRESENT;
   }

   for (uint32_t i = 0; i < info->stageCount; i++) {
      if(stages[i].stage >= MESA_SHADER_RAYGEN && stages[i].stage <= MESA_SHADER_CALLABLE) {
         printf("LVP: Registering shader stage %d with GPGPU-Sim\n", i);
         stages[i].bin = (void *)gpgpusim_registerShader(shaderPaths[i], (uint32_t)(stages[i].stage));
         assert((uint64_t)(stages[i].bin) == i);
      }
   }

   return result;
}


static VkResult
lvp_ray_tracing_pipeline_create(
    VkDevice                                    _device,
    struct lvp_pipeline_cache *                  cache,
    const VkRayTracingPipelineCreateInfoKHR*    pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkPipeline*                                 pPipeline)
{
   LVP_FROM_HANDLE(lvp_device, device, _device);
   LVP_FROM_HANDLE(lvp_pipeline_layout, pipeline_layout, pCreateInfo->layout);
   VkResult result;

   assert(pCreateInfo->sType == VK_STRUCTURE_TYPE_RAY_TRACING_PIPELINE_CREATE_INFO_KHR);
   result = vsim_validate_ray_tracing_pipeline_capabilities(device,
                                                            pCreateInfo);
   if (result != VK_SUCCESS)
      return result;

   // Create ray tracing pipeline
   struct lvp_pipeline *pipeline;
   pipeline = vk_zalloc(&device->vk.alloc, sizeof(*pipeline), 8,
                         VK_SYSTEM_ALLOCATION_SCOPE_OBJECT);
   if (pipeline == NULL)
      return vk_error(device, VK_ERROR_OUT_OF_HOST_MEMORY);
   pipeline->group_count = pCreateInfo->groupCount;
   pipeline->group_handles = vk_zalloc(&device->vk.alloc, 
         sizeof(*pipeline->group_handles) * pipeline->group_count,
         8, VK_SYSTEM_ALLOCATION_SCOPE_OBJECT);
   if (pipeline->group_handles == NULL) {
      vk_free(&device->vk.alloc, pipeline);
      return vk_error(device, VK_ERROR_OUT_OF_HOST_MEMORY);
   }
   for (uint32_t i = 0; i < pipeline->group_count; i++) {
      pipeline->group_handles[i].general_index = VK_SHADER_UNUSED_KHR;
      pipeline->group_handles[i].intersection_index = VK_SHADER_UNUSED_KHR;
      pipeline->group_handles[i].any_hit_index = VK_SHADER_UNUSED_KHR;
   }
   
   
   vk_object_base_init(&device->vk, &pipeline->base,
                       VK_OBJECT_TYPE_PIPELINE);

   result = lvp_ray_tracing_pipeline_init(pipeline, device, cache, pCreateInfo);
   if (result != VK_SUCCESS) {
      vk_free(&device->vk.alloc, pipeline);
      return result;
   }


   // Ray tracing shaders
   result = vsim_compile_ray_tracing_pipeline(pipeline, pCreateInfo);
   if (result != VK_SUCCESS) {
      vk_free(&device->vk.alloc, pipeline->group_handles);
      vk_free(&device->vk.alloc, pipeline);
      return result;
   }

   // Allocate memory for shader groups
   // Don't need the actual binary since GPGPU-Sim runs PTX

   // Need pipeline group handles
   for (unsigned i=0; i<pipeline->group_count; i++) {
      const VkRayTracingShaderGroupCreateInfoKHR *group_info = &pCreateInfo->pGroups[i];
      switch (group_info->type) {
      // TODO: AMD adds 2 to each index (not sure why...)
      case VK_RAY_TRACING_SHADER_GROUP_TYPE_GENERAL_KHR:
         printf("LVP: Adding group handle for general group: \n");
         if (group_info->generalShader != VK_SHADER_UNUSED_KHR) {
            pipeline->group_handles[i].general_index = group_info->generalShader;
            printf("\tgeneral_index %d\n", group_info->generalShader);
         }
         break;
      case VK_RAY_TRACING_SHADER_GROUP_TYPE_PROCEDURAL_HIT_GROUP_KHR:
         printf("LVP: Adding group handle for procedural hit group: \n");
         if (group_info->closestHitShader != VK_SHADER_UNUSED_KHR) {
            pipeline->group_handles[i].closest_hit_index = group_info->closestHitShader;
            printf("\tclosest_hit_index %d\n", group_info->closestHitShader);
         }
         if (group_info->intersectionShader != VK_SHADER_UNUSED_KHR) {
            pipeline->group_handles[i].intersection_index = group_info->intersectionShader;
            printf("\tintersection_index %d\n", group_info->intersectionShader);
         }
         if (group_info->anyHitShader != VK_SHADER_UNUSED_KHR) {
            pipeline->group_handles[i].any_hit_index = group_info->anyHitShader;
            printf("\tany_hit_index %d\n", group_info->anyHitShader);
         }
         break;
      case VK_RAY_TRACING_SHADER_GROUP_TYPE_TRIANGLES_HIT_GROUP_KHR:
         printf("LVP: Adding group handle for triangle hit group: \n");
         if (group_info->closestHitShader != VK_SHADER_UNUSED_KHR) {
            pipeline->group_handles[i].closest_hit_index = group_info->closestHitShader;
            printf("\tclosest_hit_index %d\n", group_info->closestHitShader);
         }
         if (group_info->anyHitShader != VK_SHADER_UNUSED_KHR) {
            pipeline->group_handles[i].any_hit_index = group_info->anyHitShader;
            printf("\tany_hit_index %d\n", group_info->anyHitShader);
         }
         break;
      case VK_SHADER_GROUP_SHADER_MAX_ENUM_KHR:
         unreachable("VK_SHADER_GROUP_SHADER_MAX_ENUM_KHR");
         break;
      default:
         unreachable("Undefined hit group type");
         break;
      }
   }

   // TODO: Add VK_PIPELINE_CREATE_RAY_TRACING_SHADER_GROUP_HANDLE_CAPTURE_REPLAY_BIT_KHR

   gpgpusim_setPipelineInfo(pCreateInfo);
   *pPipeline = lvp_pipeline_to_handle(pipeline);

   return result;
}


VkResult
lvp_CreateRayTracingPipelinesKHR(
    VkDevice                                    _device,
    VkDeferredOperationKHR                      deferredOperation,
    VkPipelineCache                             pipelineCache,
    uint32_t                                    createInfoCount,
    const VkRayTracingPipelineCreateInfoKHR*    pCreateInfos,
    const VkAllocationCallbacks*                pAllocator,
    VkPipeline*                                 pPipelines)
{
   printf("LVP: Creating ray tracing pipeline...\n");
   LVP_FROM_HANDLE(lvp_pipeline_cache, pipeline_cache, pipelineCache);

   // Assume only 1 pipeline currently
   if (createInfoCount > 1) {
      unreachable("Unimplemented");
   }

   VkResult result = lvp_ray_tracing_pipeline_create(_device, pipeline_cache,
                                                     &pCreateInfos[0],
                                                     pAllocator, &pPipelines[0]);

   return result;
}


VkResult
lvp_GetRayTracingShaderGroupHandlesKHR(
    VkDevice                                    device,
    VkPipeline                                  _pipeline,
    uint32_t                                    firstGroup,
    uint32_t                                    groupCount,
    size_t                                      dataSize,
    void*                                       pData)
{
   printf("LVP: Get ray tracing shader group handles...\n");
   LVP_FROM_HANDLE(lvp_pipeline, pipeline, _pipeline);

   // Handle size is 32 (from GetDeviceProperties); matches Intel and AMD
   #define PIPELINE_HANDLE_SIZE 32
   assert(sizeof(*pipeline->group_handles) <= PIPELINE_HANDLE_SIZE);

   // Copy handles to pData
   memset(pData, 0, groupCount * PIPELINE_HANDLE_SIZE);
   for (unsigned i = 0; i < groupCount; i++) {
      printf("LVP: Copying handle %d to %p\n", i, pData + i * PIPELINE_HANDLE_SIZE);
      memcpy(pData + i * PIPELINE_HANDLE_SIZE, 
             &pipeline->group_handles[firstGroup + i], 
             sizeof(*pipeline->group_handles));
   }

   return VK_SUCCESS;
}
