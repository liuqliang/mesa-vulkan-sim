# Copyright (c) 2022, Mohammadreza Saed, Yuan Hsi Chou, Lufei Liu, Tor M. Aamodt,
# The University of British Columbia
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution. Neither the name of
# The University of British Columbia nor the names of its contributors may be
# used to endorse or promote products derived from this software without
# specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from enum import unique
from ptx_parser import *
import sys
import os
import re

import rtcore_abi_v04_generated as rtcore_abi_v04


class Intersection_Table_Type(Enum):
    Baseline = auto()
    FCC = auto()

intersection_table_type = Intersection_Table_Type.Baseline

RTCORE_BOOTSTRAP_CONTEXT_BASE = 0x10000000
RTCORE_CONTEXT_ALIGNMENT = 0x40
RTCORE_CONTEXT_BYTES = 0x140
RTCORE_MAX_LANES_PER_WARP = 32
RTCORE_MAX_CONTEXTS_PER_TRACE_SITE = 1 << 18
RTCORE_MAX_TRACE_SITES = 8
RTCORE_MAX_LAUNCH_WIDTH = 512
RTCORE_MAX_LAUNCH_HEIGHT = 512
RTCORE_MAX_WINDOWS_PER_TRACE_SITE = (
    RTCORE_MAX_CONTEXTS_PER_TRACE_SITE // RTCORE_MAX_LANES_PER_WARP
)
RTCORE_CONTEXT_WARP_BYTES = RTCORE_MAX_LANES_PER_WARP * RTCORE_CONTEXT_BYTES
RTCORE_CONTEXT_TRACE_SITE_BYTES = (
    RTCORE_MAX_CONTEXTS_PER_TRACE_SITE * RTCORE_CONTEXT_BYTES
)
RTCORE_BOOTSTRAP_HANDOFF_WINDOW_BASE = 0x40000000
RTCORE_HANDOFF_WINDOW_ALIGNMENT = 0x80
RTCORE_HANDOFF_WINDOW_SLOT_BYTES = 0x80
RTCORE_HANDOFF_WINDOW_WARP_BYTES = RTCORE_MAX_LANES_PER_WARP * RTCORE_HANDOFF_WINDOW_SLOT_BYTES
RTCORE_HANDOFF_TRACE_SITE_BYTES = (
    RTCORE_MAX_WINDOWS_PER_TRACE_SITE * RTCORE_HANDOFF_WINDOW_WARP_BYTES
)
RTCORE_DRIVER_RUNTIME_DEFAULT_CONTEXT_BASE = RTCORE_BOOTSTRAP_CONTEXT_BASE
RTCORE_DRIVER_RUNTIME_DEFAULT_HANDOFF_WINDOW_BASE = RTCORE_BOOTSTRAP_HANDOFF_WINDOW_BASE
RTCORE_DRIVER_RUNTIME_DEFAULT_OWNERSHIP_SOURCE = 'default_runtime_owned'
RTCORE_DRIVER_RUNTIME_LAUNCH_ALLOCATION_INTERFACE_ENV = 'VULKAN_SIM_RTCORE_DRIVER_RUNTIME_LAUNCH_ALLOCATION_INTERFACE'
RTCORE_DRIVER_RUNTIME_LAUNCH_ALLOCATION_INTERFACE_V0 = 'driver_runtime_launch_allocation_v0'
RTCORE_DRIVER_RUNTIME_RETIRE_FREE_POLICY = 'retire_context_releases_lane_slot_and_token'
RTCORE_CONTEXT_V03_FIELD_OFFSETS = {
    'context_header': 0x000,
    'as_handle_or_traversable_ref': 0x008,
    'ray_origin_x': 0x010,
    'ray_tmin': 0x01c,
    'ray_direction_x': 0x020,
    'ray_tmax': 0x02c,
    'ray_flags': 0x030,
    'cull_mask': 0x034,
    'sbt_offset': 0x038,
    'sbt_stride': 0x03c,
    'miss_index': 0x040,
    'sbt_hit_base': 0x048,
    'sbt_hit_stride': 0x050,
    'sbt_hit_size': 0x054,
    'sbt_miss_base': 0x058,
    'sbt_miss_stride': 0x060,
    'sbt_miss_size': 0x064,
    'sbt_callable_base': 0x068,
    'sbt_callable_stride': 0x070,
    'sbt_callable_size': 0x074,
    'pipeline_profile_id': 0x078,
    'bvh_format_profile_id': 0x07c,
    'payload_region': 0x080,
    'hit_state_region': 0x0c0,
}
RTCORE_DRIVER_RUNTIME_HANDLE_BRIDGE_ENV = 'VULKAN_SIM_RTCORE_DRIVER_RUNTIME_HANDLE_BRIDGE'
RTCORE_DRIVER_RUNTIME_HANDLE_SCAFFOLD_ENV = 'VULKAN_SIM_RTCORE_DRIVER_RUNTIME_HANDLE_SCAFFOLD'
RTCORE_DRIVER_RUNTIME_CONTEXT_BASE_ENV = 'VULKAN_SIM_RTCORE_DRIVER_RUNTIME_CONTEXT_BASE'
RTCORE_DRIVER_RUNTIME_HANDOFF_WINDOW_BASE_ENV = 'VULKAN_SIM_RTCORE_DRIVER_RUNTIME_HANDOFF_WINDOW_BASE'
RTCORE_DISPATCH_DESCRIPTOR_V0_SCHEMA = 'rtcore_dispatch_descriptor_v0'
RTCORE_DISPATCH_DESCRIPTOR_BASE_SOURCE_SCAFFOLD_HIDDEN_BASE = 'scaffold_hidden_base'
RTCORE_DISPATCH_DESCRIPTOR_BASE_SOURCE_RUNTIME = 'runtime'
RTCORE_DISPATCH_DESCRIPTOR_BASE_SOURCE_BOOTSTRAP_COMPAT = 'bootstrap_compat'
RTCORE_DISPATCH_DESCRIPTOR_ALLOWED_BASE_SOURCES = (
    RTCORE_DISPATCH_DESCRIPTOR_BASE_SOURCE_SCAFFOLD_HIDDEN_BASE,
    RTCORE_DISPATCH_DESCRIPTOR_BASE_SOURCE_RUNTIME,
    RTCORE_DISPATCH_DESCRIPTOR_BASE_SOURCE_BOOTSTRAP_COMPAT,
)
RTCORE_CUSTOM_ABI_LOWERING_EVIDENCE_SCHEMA = 'rtcore_custom_abi_lowering_evidence_v0'
RTCORE_PATH_MODE_POLICY_CUSTOM = 'custom'
RTCORE_PATH_MODE_POLICY_LEGACY = 'legacy'
RTCORE_PATH_MODE_POLICY_INVALID = 'invalid'
RTCORE_PATH_MODE_LEGACY_ALIASES = (
    'legacy',
    'trace_ray',
    'trace-ray',
    'trace_ray_only',
    'trace-ray-only',
)
RTCORE_PATH_MODE_CUSTOM_ALIASES = (
    'custom',
    'forward',
    'forward_sideband',
    'forward-sideband',
    'sideband',
)
RTCORE_CONTINUATION_MODEL_OFF = 'off'
RTCORE_CONTINUATION_MODEL_SYNTHETIC_SPLIT = 'synthetic_split'
RTCORE_CONTINUATION_MODEL_ORACLE_SHADER_BOUNDARY = 'oracle_shader_boundary'
RTCORE_ABI_V04_SHADOW_PUBLICATION_ENV = (
    'VULKAN_SIM_RTCORE_ABI_V04_SHADOW_PUBLICATION'
)
RTCORE_ABI_V04_SHADOW_SHADER_RETURN_PUBLICATION_ENV = (
    'VULKAN_SIM_RTCORE_ABI_V04_SHADOW_SHADER_RETURN_PUBLICATION'
)
RTCORE_ABI_V04_SHADER_BUILTIN_CONSUMER_ENV = (
    'VULKAN_SIM_RTCORE_ABI_V04_SHADER_BUILTIN_CONSUMER'
)
RTCORE_V04_SUPPORTED_DIRECT_HIT_BUILTINS = (
    (
        FunctionalType.load_ray_instance_custom_index,
        'load_ray_instance_custom_index',
        'InstanceCustomIndex',
        'instance_custom_index',
    ),
    (
        FunctionalType.load_primitive_id,
        'load_primitive_id',
        'PrimitiveId',
        'primitive_index',
    ),
)


def rtcore_env_flag_enabled(name):
    value = os.environ.get(name, '0')
    return value != '' and value != '0'


def rtcore_path_mode():
    return os.environ.get('VULKAN_SIM_RTCORE_PATH_MODE', '').strip().lower()


def rtcore_path_mode_compat_custom_enabled():
    return (
        rtcore_env_flag_enabled('VULKAN_SIM_RTCORE_SYMBOLIC_SUBMIT') or
        rtcore_env_flag_enabled('VULKAN_SIM_RTCORE_FORWARD_SIDEBAND_PATH') or
        rtcore_env_flag_enabled('VULKAN_SIM_RTCORE_COMPILER_DRIVER_PUBLICATION_SOURCE')
    )


def rtcore_continuation_model():
    return os.environ.get('VULKAN_SIM_RTCORE_CONTINUATION_MODEL', '')


def rtcore_validate_custom_continuation_model():
    model = rtcore_continuation_model()
    if model == '' or model == RTCORE_CONTINUATION_MODEL_ORACLE_SHADER_BOUNDARY:
        return
    if model in (
            RTCORE_CONTINUATION_MODEL_OFF,
            RTCORE_CONTINUATION_MODEL_SYNTHETIC_SPLIT):
        raise ValueError(
            'custom symbolic RT path requires oracle_shader_boundary; '
            '%s is not a shader-complete execution model; ' % model +
            'use VULKAN_SIM_RTCORE_PATH_MODE=legacy for the supported '
            'no-continuation fallback'
        )
    raise ValueError(
        'invalid VULKAN_SIM_RTCORE_CONTINUATION_MODEL: %s' % model
    )


def rtcore_get_path_mode_policy():
    mode = rtcore_path_mode()
    if mode in RTCORE_PATH_MODE_LEGACY_ALIASES:
        return RTCORE_PATH_MODE_POLICY_LEGACY
    if mode in RTCORE_PATH_MODE_CUSTOM_ALIASES:
        return RTCORE_PATH_MODE_POLICY_CUSTOM
    if mode != '':
        return RTCORE_PATH_MODE_POLICY_INVALID
    if rtcore_env_flag_enabled('VULKAN_SIM_RTCORE_LEGACY_TRACE_RAY_PATH'):
        return RTCORE_PATH_MODE_POLICY_LEGACY
    if rtcore_path_mode_compat_custom_enabled():
        return RTCORE_PATH_MODE_POLICY_CUSTOM
    return RTCORE_PATH_MODE_POLICY_CUSTOM


def rtcore_fail_closed_on_invalid_path_mode(policy):
    if policy == RTCORE_PATH_MODE_POLICY_INVALID:
        raise ValueError(
            'invalid VULKAN_SIM_RTCORE_PATH_MODE: %s' % os.environ.get(
                'VULKAN_SIM_RTCORE_PATH_MODE', ''
            )
        )


def rtcore_path_mode_policy_legacy_path_enabled(policy):
    rtcore_fail_closed_on_invalid_path_mode(policy)
    return policy == RTCORE_PATH_MODE_POLICY_LEGACY


def rtcore_path_mode_policy_enables_custom_path(policy):
    rtcore_fail_closed_on_invalid_path_mode(policy)
    return policy == RTCORE_PATH_MODE_POLICY_CUSTOM


def rtcore_legacy_trace_ray_path_enabled():
    policy = rtcore_get_path_mode_policy()
    return rtcore_path_mode_policy_legacy_path_enabled(policy)


def rtcore_forward_sideband_path_enabled():
    policy = rtcore_get_path_mode_policy()
    return rtcore_path_mode_policy_enables_custom_path(policy)


def rtcore_symbolic_submit_enabled():
    policy = rtcore_get_path_mode_policy()
    if rtcore_path_mode_policy_legacy_path_enabled(policy):
        return False
    enabled = rtcore_path_mode_policy_enables_custom_path(policy)
    if enabled:
        rtcore_validate_custom_continuation_model()
    return enabled


def rtcore_compiler_driver_publication_source_enabled():
    policy = rtcore_get_path_mode_policy()
    if rtcore_path_mode_policy_legacy_path_enabled(policy):
        return False
    return rtcore_path_mode_policy_enables_custom_path(policy)


def rtcore_v04_shadow_publication_enabled():
    raw_value = os.environ.get(RTCORE_ABI_V04_SHADOW_PUBLICATION_ENV)
    if raw_value is None or raw_value.strip().lower() in (
        '', '0', 'false', 'off', 'no', 'disabled'
    ):
        return False
    if raw_value.strip().lower() not in (
        '1', 'true', 'on', 'yes', 'enabled'
    ):
        raise ValueError(
            'invalid %s: %s' %
            (RTCORE_ABI_V04_SHADOW_PUBLICATION_ENV, raw_value)
        )
    policy = rtcore_get_path_mode_policy()
    if not rtcore_path_mode_policy_enables_custom_path(policy):
        raise ValueError(
            '%s requires the custom RT path' %
            RTCORE_ABI_V04_SHADOW_PUBLICATION_ENV
        )
    if rtcore_abi_v04.LANE_SLOT_BYTES != RTCORE_HANDOFF_WINDOW_SLOT_BYTES:
        raise ValueError(
            'V0.4 shadow lane-slot size %u does not match compiler arena %u' %
            (
                rtcore_abi_v04.LANE_SLOT_BYTES,
                RTCORE_HANDOFF_WINDOW_SLOT_BYTES,
            )
        )
    return True


def rtcore_v04_shadow_shader_return_publication_enabled():
    raw_value = os.environ.get(
        RTCORE_ABI_V04_SHADOW_SHADER_RETURN_PUBLICATION_ENV
    )
    if raw_value is None or raw_value.strip().lower() in (
        '', '0', 'false', 'off', 'no', 'disabled'
    ):
        return False
    if raw_value.strip().lower() not in (
        '1', 'true', 'on', 'yes', 'enabled'
    ):
        raise ValueError(
            'invalid %s: %s' %
            (RTCORE_ABI_V04_SHADOW_SHADER_RETURN_PUBLICATION_ENV, raw_value)
        )
    if not rtcore_v04_shadow_publication_enabled():
        raise ValueError(
            '%s requires %s' % (
                RTCORE_ABI_V04_SHADOW_SHADER_RETURN_PUBLICATION_ENV,
                RTCORE_ABI_V04_SHADOW_PUBLICATION_ENV,
            )
        )
    return True


def rtcore_v04_shader_builtin_consumer_enabled():
    raw_value = os.environ.get(RTCORE_ABI_V04_SHADER_BUILTIN_CONSUMER_ENV)
    if raw_value is None or raw_value.strip().lower() in (
        '', '0', 'false', 'off', 'no', 'disabled'
    ):
        return False
    if raw_value.strip().lower() not in (
        '1', 'true', 'on', 'yes', 'enabled'
    ):
        raise ValueError(
            'invalid %s: %s' %
            (RTCORE_ABI_V04_SHADER_BUILTIN_CONSUMER_ENV, raw_value)
        )
    if not rtcore_v04_shadow_publication_enabled():
        raise ValueError(
            '%s requires %s' % (
                RTCORE_ABI_V04_SHADER_BUILTIN_CONSUMER_ENV,
                RTCORE_ABI_V04_SHADOW_PUBLICATION_ENV,
            )
        )
    return True


def rtcore_v04_field_spec(field_name):
    try:
        return rtcore_abi_v04.FIELD_SPECS[field_name]
    except KeyError:
        raise ValueError('missing V0.4 generated field: %s' % field_name)


def rtcore_v04_direct_field_byte_offset(field_name):
    word, lsb, width, mask = rtcore_v04_field_spec(field_name)
    if lsb != 0 or width != 32 or mask != 0xffffffff:
        raise ValueError(
            'V0.4 direct-store field is not a complete word: %s' % field_name
        )
    return word * 4


def rtcore_v04_u64_field_byte_offset(low_field, high_field):
    low_word, low_lsb, low_width, low_mask = rtcore_v04_field_spec(low_field)
    high_word, high_lsb, high_width, high_mask = rtcore_v04_field_spec(
        high_field
    )
    if (
        low_lsb != 0 or low_width != 32 or low_mask != 0xffffffff or
        high_lsb != 0 or high_width != 32 or high_mask != 0xffffffff or
        high_word != low_word + 1
    ):
        raise ValueError(
            'V0.4 u64 fields are not adjacent complete words: %s/%s' %
            (low_field, high_field)
        )
    return low_word * 4


def rtcore_v04_unsigned_integer_literal(operand):
    text = operand.strip()
    match = re.fullmatch(
        r'(?P<sign>[+-]?)(?P<body>'
        r'0[xX][0-9a-fA-F]+|0[bB][01]+|0[0-7]*|[1-9][0-9]*'
        r')(?P<suffix>[uU](?:[lL]{1,2})?|[lL]{1,2}[uU]?)?',
        text,
    )
    if match is None:
        return None
    body = match.group('body')
    if body.lower().startswith('0x'):
        base = 16
        digits = body[2:]
    elif body.lower().startswith('0b'):
        base = 2
        digits = body[2:]
    elif len(body) > 1 and body.startswith('0'):
        base = 8
        digits = body[1:]
    else:
        base = 10
        digits = body
    value = int(digits or '0', base)
    return -value if match.group('sign') == '-' else value


def rtcore_v04_validate_packed_literal(field_name, operand):
    value = rtcore_v04_unsigned_integer_literal(operand)
    if value is None:
        return
    _word, _lsb, width, _mask = rtcore_v04_field_spec(field_name)
    if value < 0 or value >= (1 << width):
        raise ValueError(
            'V0.4 shadow %s literal %s does not fit %u bits' %
            (field_name, operand, width)
        )


def rtcore_conditioned_functional_line(
    leading_whitespace,
    condition,
    function,
    args,
):
    generated = PTXFunctionalLine()
    generated.leadingWhiteSpace = leading_whitespace
    generated.condition = condition or ''
    generated.buildString(function, args)
    return generated


def rtcore_v04_handoff_word_address(lane_ptr_reg, byte_offset):
    if byte_offset == 0:
        return '[%s]' % lane_ptr_reg
    return '[%s + %u]' % (lane_ptr_reg, byte_offset)


def rtcore_v04_shadow_trace_input_publication_lines(
    leading_whitespace,
    trace_ray_condition,
    trace_ray_id,
    lane_ptr_reg,
    context_ptr_reg,
    traversable_reference,
    ray_flags,
    cull_mask,
    sbt_record_offset,
    sbt_record_stride,
    miss_index,
    origin_regs,
    ray_tmin,
    direction_regs,
    ray_tmax,
):
    packed_w13_reg = '%%rt_v04_shadow_trace_input_w13_%u' % trace_ray_id
    pack_tmp_reg = '%%rt_v04_shadow_pack_tmp_%u' % trace_ray_id
    store_b32_reg = '%%rt_v04_shadow_store_b32_%u' % trace_ray_id
    store_b64_reg = '%%rt_v04_shadow_store_b64_%u' % trace_ray_id
    zero_reg = '%%rt_v04_shadow_zero_%u' % trace_ray_id

    marker = PTXLine('')
    marker.fullLine = (
        leading_whitespace + '// rtcore_v04_shadow_trace_input_publication ' +
        'profile=' + rtcore_abi_v04.PROFILE_ID + ' source_sha256=' +
        rtcore_abi_v04.SOURCE_INPUT_SHA256 + '\n'
    )
    declarations = []
    for register_name, register_type in (
        (packed_w13_reg, '.b32'),
        (pack_tmp_reg, '.b32'),
        (store_b32_reg, '.b32'),
        (store_b64_reg, '.b64'),
        (zero_reg, '.b32'),
    ):
        declaration = PTXDecleration()
        declaration.leadingWhiteSpace = leading_whitespace
        declaration.buildString(
            DeclarationType.Register,
            None,
            register_type,
            register_name,
        )
        declarations.append(declaration)

    lines = [marker] + declarations

    direct_u64_fields = (
        (
            'context_address_low32',
            'context_address_high32',
            context_ptr_reg,
        ),
        (
            'traversable_reference_low32',
            'traversable_reference_high32',
            traversable_reference,
        ),
    )
    for low_field, high_field, value in direct_u64_fields:
        byte_offset = rtcore_v04_u64_field_byte_offset(low_field, high_field)
        lines.append(rtcore_conditioned_functional_line(
            leading_whitespace,
            trace_ray_condition,
            'mov.b64',
            (store_b64_reg, value),
        ))
        lines.append(rtcore_conditioned_functional_line(
            leading_whitespace,
            trace_ray_condition,
            'st.global.b64',
            (
                rtcore_v04_handoff_word_address(lane_ptr_reg, byte_offset),
                store_b64_reg,
            ),
        ))

    direct_b32_fields = (
        ('world_ray_origin_x_fp32', origin_regs[0]),
        ('world_ray_origin_y_fp32', origin_regs[1]),
        ('world_ray_origin_z_fp32', origin_regs[2]),
        ('ray_tmin_fp32', ray_tmin),
        ('world_ray_direction_x_fp32', direction_regs[0]),
        ('world_ray_direction_y_fp32', direction_regs[1]),
        ('world_ray_direction_z_fp32', direction_regs[2]),
        ('launch_ray_tmax_fp32', ray_tmax),
        ('ray_flags', ray_flags),
    )
    for field_name, value in direct_b32_fields:
        byte_offset = rtcore_v04_direct_field_byte_offset(field_name)
        lines.append(rtcore_conditioned_functional_line(
            leading_whitespace,
            trace_ray_condition,
            'mov.b32',
            (store_b32_reg, value),
        ))
        lines.append(rtcore_conditioned_functional_line(
            leading_whitespace,
            trace_ray_condition,
            'st.global.b32',
            (
                rtcore_v04_handoff_word_address(lane_ptr_reg, byte_offset),
                store_b32_reg,
            ),
        ))

    packed_fields = (
        ('cull_mask', cull_mask),
        ('sbt_record_offset', sbt_record_offset),
        ('sbt_record_stride', sbt_record_stride),
        ('miss_index', miss_index),
    )
    packed_word = None
    lines.append(rtcore_conditioned_functional_line(
        leading_whitespace,
        trace_ray_condition,
        'mov.b32',
        (packed_w13_reg, '0'),
    ))
    for field_name, value in packed_fields:
        rtcore_v04_validate_packed_literal(field_name, value)
        word, lsb, width, _mask = rtcore_v04_field_spec(field_name)
        if packed_word is None:
            packed_word = word
        elif word != packed_word:
            raise ValueError('V0.4 trace policy fields do not share one word')
        lines.append(rtcore_conditioned_functional_line(
            leading_whitespace,
            trace_ray_condition,
            'and.b32',
            (pack_tmp_reg, value, str((1 << width) - 1)),
        ))
        if lsb != 0:
            lines.append(rtcore_conditioned_functional_line(
                leading_whitespace,
                trace_ray_condition,
                'shl.b32',
                (pack_tmp_reg, pack_tmp_reg, str(lsb)),
            ))
        lines.append(rtcore_conditioned_functional_line(
            leading_whitespace,
            trace_ray_condition,
            'or.b32',
            (packed_w13_reg, packed_w13_reg, pack_tmp_reg),
        ))
    if packed_word is None:
        raise ValueError('V0.4 trace policy word has no generated fields')
    lines.append(rtcore_conditioned_functional_line(
        leading_whitespace,
        trace_ray_condition,
        'st.global.b32',
        (
            rtcore_v04_handoff_word_address(lane_ptr_reg, packed_word * 4),
            packed_w13_reg,
        ),
    ))

    fully_reserved_words = tuple(
        index for index, mask in enumerate(rtcore_abi_v04.RESERVED_MASKS)
        if mask == 0xffffffff
    )
    lines.append(rtcore_conditioned_functional_line(
        leading_whitespace,
        trace_ray_condition,
        'mov.b32',
        (zero_reg, '0'),
    ))
    for word in fully_reserved_words:
        lines.append(rtcore_conditioned_functional_line(
            leading_whitespace,
            trace_ray_condition,
            'st.global.b32',
            (
                rtcore_v04_handoff_word_address(lane_ptr_reg, word * 4),
                zero_reg,
            ),
        ))
    lines.append(rtcore_conditioned_functional_line(
        leading_whitespace,
        trace_ray_condition,
        'membar.gl',
        (),
    ))
    return lines


def rtcore_parse_int_env(name, fallback):
    value = os.environ.get(name)
    if value is None or value == '':
        return fallback
    try:
        return int(value, 0)
    except ValueError:
        return fallback


def rtcore_driver_runtime_handle_scaffold_enabled():
    value = os.environ.get(RTCORE_DRIVER_RUNTIME_HANDLE_SCAFFOLD_ENV)
    if value is None or value == '':
        return True
    value = value.strip().lower()
    if value in ('0', 'false', 'off', 'no'):
        return False
    if value in ('1', 'true', 'on', 'yes'):
        return True
    raise ValueError(
        'invalid VULKAN_SIM_RTCORE_DRIVER_RUNTIME_HANDLE_SCAFFOLD: %s' % value
    )


def rtcore_parse_driver_runtime_int_env(name, fallback):
    value = os.environ.get(name)
    if value is None or value == '':
        return fallback
    try:
        return int(value, 0)
    except ValueError:
        raise ValueError('invalid %s: %s' % (name, value))


def rtcore_parse_required_driver_runtime_int_env(name):
    value = os.environ.get(name)
    if value is None or value == '':
        raise ValueError('missing %s for driver/runtime handle scaffold' % name)
    try:
        return int(value, 0)
    except ValueError:
        raise ValueError('invalid %s: %s' % (name, value))


def rtcore_driver_runtime_handle_bridge_mode():
    value = os.environ.get(RTCORE_DRIVER_RUNTIME_HANDLE_BRIDGE_ENV)
    if value is None or value == '':
        if not rtcore_driver_runtime_handle_scaffold_enabled():
            return 'bootstrap_compat'
        return 'driver_runtime_handle_bridge'
    value = value.strip().lower()
    if value in (
        '1',
        'true',
        'on',
        'yes',
        'default',
        'driver_runtime',
        'driver-runtime',
        'driver_runtime_handle_bridge',
        'driver-runtime-handle-bridge',
        'bridge',
    ):
        return 'driver_runtime_handle_bridge'
    if value in (
        'bootstrap',
        'bootstrap_compat',
        'bootstrap-compat',
        'scaffold',
        'compat',
    ):
        return 'bootstrap_compat'
    if value in ('0', 'false', 'off', 'no', 'legacy', 'legacy_opt_out'):
        return 'legacy_opt_out'
    raise ValueError(
        'invalid VULKAN_SIM_RTCORE_DRIVER_RUNTIME_HANDLE_BRIDGE: %s' % value
    )


def rtcore_validate_driver_runtime_base_alignment(name, value, alignment):
    if value % alignment != 0:
        raise ValueError(
            'invalid %s alignment: 0x%x is not %u-byte aligned' %
            (name, value, alignment)
        )


def rtcore_driver_runtime_launch_allocation_interface():
    value = os.environ.get(RTCORE_DRIVER_RUNTIME_LAUNCH_ALLOCATION_INTERFACE_ENV)
    if value is None or value == '':
        return RTCORE_DRIVER_RUNTIME_LAUNCH_ALLOCATION_INTERFACE_V0
    value = value.strip().lower()
    if value in (
        '1',
        'true',
        'on',
        'yes',
        'default',
        RTCORE_DRIVER_RUNTIME_LAUNCH_ALLOCATION_INTERFACE_V0,
        'driver-runtime-launch-allocation-v0',
    ):
        return RTCORE_DRIVER_RUNTIME_LAUNCH_ALLOCATION_INTERFACE_V0
    raise ValueError(
        'invalid %s: %s' %
        (RTCORE_DRIVER_RUNTIME_LAUNCH_ALLOCATION_INTERFACE_ENV, value)
    )


def rtcore_driver_runtime_launch_allocation_descriptor(trace_ray_id):
    mode = rtcore_driver_runtime_handle_bridge_mode()
    if mode in ('bootstrap_compat', 'legacy_opt_out'):
        context_base = RTCORE_BOOTSTRAP_CONTEXT_BASE
        handoff_base = rtcore_symbolic_handoff_window_base()
    elif not rtcore_driver_runtime_handle_scaffold_enabled():
        context_base = RTCORE_BOOTSTRAP_CONTEXT_BASE
        handoff_base = rtcore_symbolic_handoff_window_base()
    else:
        context_base = rtcore_parse_driver_runtime_int_env(
            RTCORE_DRIVER_RUNTIME_CONTEXT_BASE_ENV,
            RTCORE_DRIVER_RUNTIME_DEFAULT_CONTEXT_BASE,
        )
        handoff_base = rtcore_parse_driver_runtime_int_env(
            RTCORE_DRIVER_RUNTIME_HANDOFF_WINDOW_BASE_ENV,
            RTCORE_DRIVER_RUNTIME_DEFAULT_HANDOFF_WINDOW_BASE,
        )
    rtcore_validate_driver_runtime_base_alignment(
        RTCORE_DRIVER_RUNTIME_CONTEXT_BASE_ENV,
        context_base,
        RTCORE_CONTEXT_ALIGNMENT,
    )
    rtcore_validate_driver_runtime_base_alignment(
        RTCORE_DRIVER_RUNTIME_HANDOFF_WINDOW_BASE_ENV,
        handoff_base,
        RTCORE_HANDOFF_WINDOW_ALIGNMENT,
    )
    return {
        'interface': rtcore_driver_runtime_launch_allocation_interface(),
        'context_base': context_base,
        'handoff_window_base': handoff_base,
        'context_alignment': RTCORE_CONTEXT_ALIGNMENT,
        'handoff_alignment': RTCORE_HANDOFF_WINDOW_ALIGNMENT,
        'context_lane_stride_bytes': RTCORE_CONTEXT_BYTES,
        'handoff_lane_slot_stride_bytes': RTCORE_HANDOFF_WINDOW_SLOT_BYTES,
        'capacity_lane_slots': RTCORE_MAX_LANES_PER_WARP,
        'owner_generation_seed': trace_ray_id + 1,
        'retire_free_policy': RTCORE_DRIVER_RUNTIME_RETIRE_FREE_POLICY,
    }


def rtcore_driver_runtime_launch_allocation_context_base(trace_ray_id):
    descriptor = rtcore_driver_runtime_launch_allocation_descriptor(trace_ray_id)
    return str(descriptor['context_base'])


def rtcore_driver_runtime_launch_allocation_handoff_window_base(trace_ray_id):
    descriptor = rtcore_driver_runtime_launch_allocation_descriptor(trace_ray_id)
    return str(descriptor['handoff_window_base'])


def rtcore_dispatch_descriptor_base_source():
    mode = rtcore_driver_runtime_handle_bridge_mode()
    if mode in ('bootstrap_compat', 'legacy_opt_out'):
        return RTCORE_DISPATCH_DESCRIPTOR_BASE_SOURCE_BOOTSTRAP_COMPAT
    if rtcore_driver_runtime_handle_scaffold_enabled():
        return RTCORE_DISPATCH_DESCRIPTOR_BASE_SOURCE_SCAFFOLD_HIDDEN_BASE
    return RTCORE_DISPATCH_DESCRIPTOR_BASE_SOURCE_BOOTSTRAP_COMPAT


def rtcore_validate_dispatch_descriptor_v0(descriptor):
    if descriptor.get('schema') != RTCORE_DISPATCH_DESCRIPTOR_V0_SCHEMA:
        rtcore_raise_compiler_lowering_contract_violation(
            'dispatch descriptor v0 schema mismatch'
        )
    if descriptor.get('descriptor_base_source') not in RTCORE_DISPATCH_DESCRIPTOR_ALLOWED_BASE_SOURCES:
        rtcore_raise_compiler_lowering_contract_violation(
            'dispatch descriptor v0 base source is not recognized'
        )
    if descriptor.get('context_stride') != RTCORE_CONTEXT_BYTES:
        rtcore_raise_compiler_lowering_contract_violation(
            'dispatch descriptor v0 context stride mismatch'
        )
    if descriptor.get('handoff_lane_stride') != RTCORE_HANDOFF_WINDOW_SLOT_BYTES:
        rtcore_raise_compiler_lowering_contract_violation(
            'dispatch descriptor v0 handoff lane stride mismatch'
        )
    if descriptor.get('capacity_lane_slots') != RTCORE_MAX_LANES_PER_WARP:
        rtcore_raise_compiler_lowering_contract_violation(
            'dispatch descriptor v0 lane capacity mismatch'
        )
    if descriptor.get('context_base') % RTCORE_CONTEXT_ALIGNMENT != 0:
        rtcore_raise_compiler_lowering_contract_violation(
            'dispatch descriptor v0 context base alignment mismatch'
        )
    if descriptor.get('handoff_window_base') % RTCORE_HANDOFF_WINDOW_ALIGNMENT != 0:
        rtcore_raise_compiler_lowering_contract_violation(
            'dispatch descriptor v0 handoff window base alignment mismatch'
        )


def rtcore_dispatch_descriptor_v0(trace_ray_id):
    allocation = rtcore_driver_runtime_launch_allocation_descriptor(trace_ray_id)
    descriptor = {
        'schema': RTCORE_DISPATCH_DESCRIPTOR_V0_SCHEMA,
        'descriptor_base_source': rtcore_dispatch_descriptor_base_source(),
        'context_base': allocation['context_base'],
        'context_stride': allocation['context_lane_stride_bytes'],
        'handoff_window_base': allocation['handoff_window_base'],
        'handoff_lane_stride': allocation['handoff_lane_slot_stride_bytes'],
        'capacity_lane_slots': allocation['capacity_lane_slots'],
        'as_table_locator': 'compat_proxy_registry',
        'sbt_locator': 'compat_vulkan_sim_metadata',
        'launch_metadata': 'trace_ray_id_%u' % trace_ray_id,
        'allocation': allocation,
    }
    rtcore_validate_dispatch_descriptor_v0(descriptor)
    return descriptor


def rtcore_dispatch_descriptor_v0_context_base(trace_ray_id):
    descriptor = rtcore_dispatch_descriptor_v0(trace_ray_id)
    return str(descriptor['context_base'])


def rtcore_dispatch_descriptor_v0_handoff_window_base(trace_ray_id):
    descriptor = rtcore_dispatch_descriptor_v0(trace_ray_id)
    return str(descriptor['handoff_window_base'])


def rtcore_dispatch_descriptor_v0_marker(trace_ray_id, leading_whitespace):
    descriptor = rtcore_dispatch_descriptor_v0(trace_ray_id)
    marker = PTXLine('')
    marker.fullLine = (
        leading_whitespace +
        '// rtcore_dispatch_descriptor_v0 descriptor_base_source=%s '
        'context_stride=%u handoff_lane_stride=%u as_table_locator=%s '
        'sbt_locator=%s launch_metadata=%s\n'
    ) % (
        descriptor['descriptor_base_source'],
        descriptor['context_stride'],
        descriptor['handoff_lane_stride'],
        descriptor['as_table_locator'],
        descriptor['sbt_locator'],
        descriptor['launch_metadata'],
    )
    return marker


def rtcore_dispatch_descriptor_v0_preflight_marker(trace_ray_id, leading_whitespace):
    descriptor = rtcore_dispatch_descriptor_v0(trace_ray_id)
    marker = PTXLine('')
    marker.fullLine = (
        leading_whitespace +
        '// rtcore_dispatch_descriptor_v0_preflight schema=%s '
        'descriptor_validated=1 descriptor_base_source=%s '
        'capacity_lane_slots=%u context_alignment=%u handoff_alignment=%u\n'
    ) % (
        descriptor['schema'],
        descriptor['descriptor_base_source'],
        descriptor['capacity_lane_slots'],
        descriptor['allocation']['context_alignment'],
        descriptor['allocation']['handoff_alignment'],
    )
    return marker


def rtcore_context_v03_field_address_plan_marker(leading_whitespace):
    assert RTCORE_CONTEXT_V03_FIELD_OFFSETS['payload_region'] == 0x080
    assert RTCORE_CONTEXT_V03_FIELD_OFFSETS['hit_state_region'] == 0x0c0
    assert RTCORE_CONTEXT_V03_FIELD_OFFSETS['bvh_format_profile_id'] + 4 == 0x080
    marker = PTXLine('')
    marker.fullLine = (
        leading_whitespace +
        '// rtcore_context_v03_field_address_plan '
        'context_header=v_context_ptr+0x000 '
        'as_ref=v_context_ptr+0x008 ray_origin=v_context_ptr+0x010 '
        'ray_tmin=v_context_ptr+0x01c ray_direction=v_context_ptr+0x020 '
        'ray_tmax=v_context_ptr+0x02c ray_flags=v_context_ptr+0x030 '
        'cull_mask=v_context_ptr+0x034 sbt_offset=v_context_ptr+0x038 '
        'sbt_stride=v_context_ptr+0x03c miss_index=v_context_ptr+0x040 '
        'sbt_hit=v_context_ptr+0x048 sbt_miss=v_context_ptr+0x058 '
        'sbt_callable=v_context_ptr+0x068 '
        'pipeline_profile=v_context_ptr+0x078 '
        'bvh_profile=v_context_ptr+0x07c\n'
    )
    return marker


def rtcore_custom_abi_lowering_evidence_marker(trace_ray_id, leading_whitespace):
    descriptor = rtcore_dispatch_descriptor_v0(trace_ray_id)
    publish_count = 1 if rtcore_compiler_driver_publication_source_enabled() else 0
    marker = PTXLine('')
    marker.fullLine = (
        leading_whitespace +
        '// rtcore_custom_abi_lowering_evidence schema=%s trace_ray_id=%u '
        'descriptor_base_source=%s rt_publish_trace_context_count=%u '
        'rt_submit_count=%u rt_retire_context_count=%u '
        'rt_submit_operand_count=%u rt_retire_context_operand_count=%u '
        'legacy_trace_ray_primary_path=0\n'
    ) % (
        RTCORE_CUSTOM_ABI_LOWERING_EVIDENCE_SCHEMA,
        trace_ray_id,
        descriptor['descriptor_base_source'],
        publish_count,
        1,
        1,
        3,
        2,
    )
    return marker


def rtcore_bootstrap_context_base(trace_ray_id):
    return str(RTCORE_BOOTSTRAP_CONTEXT_BASE + trace_ray_id * RTCORE_CONTEXT_WARP_BYTES)


def rtcore_driver_runtime_context_base(trace_ray_id):
    return rtcore_driver_runtime_launch_allocation_context_base(trace_ray_id)


def rtcore_driver_runtime_handle_bridge_context_base(trace_ray_id):
    return rtcore_driver_runtime_launch_allocation_context_base(trace_ray_id)


def rtcore_symbolic_handoff_window_base():
    return rtcore_parse_int_env(
        'VULKAN_SIM_RTCORE_SYMBOLIC_HANDOFF_WINDOW_BASE',
        RTCORE_BOOTSTRAP_HANDOFF_WINDOW_BASE,
    )


def rtcore_bootstrap_handoff_window_base(trace_ray_id):
    return str(rtcore_symbolic_handoff_window_base() + trace_ray_id * RTCORE_HANDOFF_WINDOW_WARP_BYTES)


def rtcore_driver_runtime_handoff_window_base(trace_ray_id):
    return rtcore_driver_runtime_launch_allocation_handoff_window_base(trace_ray_id)


def rtcore_driver_runtime_handle_bridge_handoff_window_base(trace_ray_id):
    return rtcore_driver_runtime_launch_allocation_handoff_window_base(trace_ray_id)


def rtcore_raise_compiler_lowering_contract_violation(reason):
    raise ValueError('RTcore compiler lowering contract violation: %s' % reason)


def rtcore_prepare_continuation_ptx_profile(ptx_shader):
    if (not rtcore_symbolic_submit_enabled() or
            ptx_shader.getShaderType() != ShaderType.Ray_generation):
        return

    version_index = None
    target_index = None
    for index, line in enumerate(ptx_shader.lines):
        stripped = line.fullLine.strip()
        if stripped.startswith('.version '):
            version_index = index
        elif stripped.startswith('.target '):
            target_index = index

    if version_index is None:
        ptx_shader.lines.insert(0, PTXLine('.version 6.2\n'))
        version_index = 0
        if target_index is not None:
            target_index += 1
    else:
        ptx_shader.lines[version_index] = PTXLine('.version 6.2\n')

    target_line = PTXLine('.target sm_30\n')
    if target_index is None:
        ptx_shader.lines.insert(version_index + 1, target_line)
    else:
        ptx_shader.lines[target_index] = target_line


def rtcore_rebuild_conditioned_functional_line(line):
    if line is None:
        return
    line.buildString(line.functionalType, line.args)


def rtcore_copy_trace_ray_condition(
    trace_ray_condition,
    trace_ray_line=None,
    rt_submit_line=None,
    rt_publish_trace_context_line=None,
    retire_context=None,
):
    if trace_ray_line is not None:
        trace_ray_line.condition = trace_ray_condition
        rtcore_rebuild_conditioned_functional_line(trace_ray_line)
    if rt_publish_trace_context_line is not None:
        rt_publish_trace_context_line.condition = trace_ray_condition
        rtcore_rebuild_conditioned_functional_line(rt_publish_trace_context_line)
    if rt_submit_line is not None:
        rt_submit_line.condition = trace_ray_condition
        rtcore_rebuild_conditioned_functional_line(rt_submit_line)
    if retire_context is not None:
        retire_context.condition = trace_ray_condition
        rtcore_rebuild_conditioned_functional_line(retire_context)


def rtcore_validate_trace_ray_compiler_contract(
    trace_ray_line,
    rt_submit_line,
    rt_publish_trace_context_line,
    context_ptr_reg,
    handoff_window_base_reg,
    v04_shadow_publication=False,
):
    if rt_submit_line is None:
        rtcore_raise_compiler_lowering_contract_violation(
            'missing generated rt_submit line'
        )
    if len(rt_submit_line.args) != 3:
        rtcore_raise_compiler_lowering_contract_violation(
            'rt_submit operand count is %d, expected 3' % len(rt_submit_line.args)
        )
    if rt_submit_line.args[1] != context_ptr_reg:
        rtcore_raise_compiler_lowering_contract_violation(
            'rt_submit context pointer register is not the generated context register'
        )
    if rt_submit_line.args[2] != handoff_window_base_reg:
        rtcore_raise_compiler_lowering_contract_violation(
            'rt_submit handoff window register is not the generated window register'
        )
    if rt_publish_trace_context_line is None:
        return
    expected_publish_operand_count = 17 if v04_shadow_publication else 16
    if len(rt_publish_trace_context_line.args) != expected_publish_operand_count:
        rtcore_raise_compiler_lowering_contract_violation(
            'rt_publish_trace_context operand count is %d, expected %d'
            % (
                len(rt_publish_trace_context_line.args),
                expected_publish_operand_count,
            )
        )
    if rt_publish_trace_context_line.args[0] != context_ptr_reg:
        rtcore_raise_compiler_lowering_contract_violation(
            'rt_publish_trace_context context pointer register does not match rt_submit'
        )
    if rt_publish_trace_context_line.args[1] != handoff_window_base_reg:
        rtcore_raise_compiler_lowering_contract_violation(
            'rt_publish_trace_context handoff window register does not match rt_submit'
        )
    if (
        v04_shadow_publication and
        rt_publish_trace_context_line.args[16] != str(rtcore_abi_v04.LANE_SLOT_BYTES)
    ):
        rtcore_raise_compiler_lowering_contract_violation(
            'rt_publish_trace_context V0.4 handoff backing size is not the '
            'generated lane-slot size'
        )


def vector_suffix_letter(x):
    if x == 0:
        return 'x'
    elif x == 1:
        return 'y'
    elif x == 2:
        return 'z'
    elif x == 3:
        return 'w'

def vector_suffix_number(x):
    if x == 'x':
        return 0
    elif x == 'y':
        return 1
    elif x == 'z':
        return 2
    elif x == 'w':
        return 3



def unwrapp_vector(ptx_shader, vectorVariableName, unwrappedName):
    declaration, _ = ptx_shader.findDeclaration(vectorVariableName)
    assert declaration.isVector()

    newRegNames = [(unwrappedName + '_' + str(i)) for i in range(declaration.vectorSize())]

    newDeclarations = list()
    for i in range(declaration.vectorSize()):
        newDeclaration = PTXDecleration()
        newDeclaration.leadingWhiteSpace = declaration.leadingWhiteSpace
        newDeclaration.buildString(DeclarationType.Register, None, declaration.variableType, newRegNames[i])
        newDeclarations.append(newDeclaration)

    unwrapMovs = list()
    # for i in range(declaration.vectorSize()):
    #     newMov = PTXFunctionalLine()
    #     newMov.leadingWhiteSpace = declaration.leadingWhiteSpace

    #     variableType = declaration.variableType
    #     if variableType == '.b32':
    #         variableType = '.f32'
    #     elif variableType == '.b64':
    #         variableType = '.f64'
    #     zero = '0'
    #     if variableType[1] == 'f':
    #         zero = '0F00000000'
    #     newMov.buildString('add%s' % variableType, (newRegNames[i], vectorVariableName + '.' + vector_suffix_letter(i), zero))
    #     unwrapMovs.append(newMov)
    newMov = PTXFunctionalLine()
    newMov.leadingWhiteSpace = declaration.leadingWhiteSpace
    newMov.buildString('unwrap_32_4', tuple(newRegNames + [vectorVariableName, ]))
    unwrapMovs.append(newMov)
    

    wrapMovs = list()
    # for i in range(declaration.vectorSize()):
    #     wrapMov = PTXFunctionalLine()
    #     wrapMov.leadingWhiteSpace = declaration.leadingWhiteSpace
    #     variableType = declaration.variableType
    #     if variableType == '.b32':
    #         variableType = '.f32'
    #     elif variableType == '.b64':
    #         variableType = '.f64'
    #     zero = '0'
    #     if variableType[1] == 'f':
    #         zero = '0F00000000'
    #     wrapMov.buildString('add%s' % (variableType), (vectorVariableName + '.' + vector_suffix_letter(i), newRegNames[i], zero))
    #     wrapMovs.append(wrapMov)
    wrapMov = PTXFunctionalLine()
    wrapMov.leadingWhiteSpace = declaration.leadingWhiteSpace
    wrapMov.buildString('wrap_32_4', tuple([vectorVariableName, ] + newRegNames))
    wrapMovs.append(wrapMov)

    return newRegNames, newDeclarations, unwrapMovs, wrapMovs


def translate_vector_operands(ptx_shader, unique_ID):
    index = -1
    while index + 1 < len(ptx_shader.lines):
        index += 1
        line = ptx_shader.lines[index]

        if line.instructionClass == InstructionClass.Functional:
            # debug_print("#######################")
            debug_print(line.fullLine)

            # Make sure the args form a list (not a tuple)
            line.args = list(line.args)
            for argIndex in range(len(line.args)):
                arg = line.args[argIndex]
                if '.' not in arg:
                    continue

                # For regular component-wise access
                if arg[-2] == '.':
                    base_ssa = arg.split('.')[0]
                    component = arg[-1]
                    newRegName = base_ssa + '_' + str(vector_suffix_number(component))
                # For special "_bits" registers
                elif "bits" in arg:
                    assert arg[-7] == '.'
                    base_ssa = arg.split('.')[0]
                    component = arg.split('.')[1][0]
                    newRegName = base_ssa + '_' + str(vector_suffix_number(component)) + "_bits"
                else:
                    assert 0

                args = line.args
                args[argIndex] = newRegName
                line.buildString(line.fullFunction, args)
        
        elif line.instructionClass == InstructionClass.VariableDeclaration:
            if line.declarationType != DeclarationType.Register:
                continue
            if not line.isVector():
                continue

            # debug_print("#######################")
            # debug_print(line.fullLine)

            newLines = list()
            for i in range(line.vectorSize()):
                newLine = PTXDecleration()
                newLine.leadingWhiteSpace = line.leadingWhiteSpace
                newLine.buildString(line.declarationType, None, line.variableType, line.variableName + '_' + str(i))
                newLines.append(newLine)
            
            ptx_shader.lines.remove(line)
            ptx_shader.lines[index:index] = newLines



def translate_descriptor_set_instructions(ptx_shader):
    for line in ptx_shader.lines:
        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.functionalType == FunctionalType.vulkan_resource_index:
            dst, whatIsThis, descSet, binding, type = line.args

            declaration, _ = ptx_shader.findDeclaration(dst)
            declaration.buildString(declaration.declarationType, None, '.b64', declaration.variableName)

            line.buildString(FunctionalType.load_vulkan_descriptor, (dst, descSet, binding, type))
        
        elif line.functionalType == FunctionalType.load_vulkan_descriptor:
            dst, src, type = line.args

            declaration, _ = ptx_shader.findDeclaration(dst)
            declaration.buildString(declaration.declarationType, None, '.b64', declaration.variableName)

            line.buildString('mov.b64', (dst, src))

def translate_deref_instructions(ptx_shader):
    index = -1
    while index + 1 < len(ptx_shader.lines):
        index += 1
        line = ptx_shader.lines[index]
        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.functionalType == FunctionalType.deref_cast:
            dst, baseType, src, type = line.args

            declaration, _ = ptx_shader.findDeclaration(dst)
            declaration.buildString(declaration.declarationType, None, '.b64', declaration.variableName)
            declaration.pointerVariableType = '.' + baseType

            line.buildString('mov.b64', (dst, src))
        
        elif line.functionalType == FunctionalType.deref_struct:
            dst, need_deref, src, ptr, fieldName, offset, baseType, type = line.args

            declaration, _ = ptx_shader.findDeclaration(dst)
            declaration.buildString(declaration.declarationType, None, '.b64', declaration.variableName)
            declaration.pointerVariableType = '.' + baseType

            line.buildString('add.u64', (dst, src, offset))
        
        elif line.functionalType == FunctionalType.deref_array:
            dst, need_deref, src, arrayIndex, arrayStride, baseType, type = line.args

            if baseType == 'descriptor':
                # FIX: HARDCODED STRIDE SIZE OF LVP_DESCRIPTOR
                arrayStride = str(48)

            assert int(arrayStride) != 0

            declaration, _ = ptx_shader.findDeclaration(dst)
            declaration.buildString(declaration.declarationType, None, '.b64', declaration.variableName)
            declaration.pointerVariableType = '.' + baseType

            if arrayIndex[0] != '%': # const array index
                line.buildString('add.u64', (dst, src, str(int(arrayIndex) * int(arrayStride))))
            else: # reg array index

                # exit(-1)
                newLines = list()

                indexRegName_32 = dst + '_array_index_32'
                indexRegName_64 = dst + '_array_index_64'

                newDeclaration_32 = PTXDecleration()
                newDeclaration_32.leadingWhiteSpace = declaration.leadingWhiteSpace
                newDeclaration_32.buildString(DeclarationType.Register, None, '.u32', indexRegName_32)

                newDeclaration_64 = PTXDecleration()
                newDeclaration_64.leadingWhiteSpace = declaration.leadingWhiteSpace
                newDeclaration_64.buildString(DeclarationType.Register, None, '.u64', indexRegName_64)

                indexDeclaration, _ = ptx_shader.findDeclaration(arrayIndex)

                newSet = PTXFunctionalLine()
                newSet.leadingWhiteSpace = declaration.leadingWhiteSpace
                if indexDeclaration.variableType == '.u32':
                    newSet.buildString('mov.u32', (indexRegName_32, arrayIndex))
                else:
                    variableType = indexDeclaration.variableType
                    if variableType[1] == 'b':
                        variableType = '.u' + variableType[2:]
                    if variableType[1] == 'f':
                        # newSet.buildString('cvt.rni.u32%s' % variableType, (indexRegName_32, arrayIndex))
                        newSet.buildString('mov.b32', (indexRegName_32, arrayIndex))
                    else:
                        newSet.buildString('cvt.u32%s' % variableType, (indexRegName_32, arrayIndex))


                newMult = PTXFunctionalLine()
                newMult.leadingWhiteSpace = declaration.leadingWhiteSpace
                newMult.buildString('mul.wide.u32', (indexRegName_64, indexRegName_32, arrayStride))

                newAdd = PTXFunctionalLine()
                newAdd.leadingWhiteSpace = declaration.leadingWhiteSpace
                newAdd.comment = line.comment
                newAdd.buildString('add.u64', (dst, src, indexRegName_64))

                ptx_shader.lines.remove(line)
                ptx_shader.lines[index:index] = (newDeclaration_32, newDeclaration_64, newSet, newMult, newAdd)

        
        elif line.functionalType == FunctionalType.load_deref:
            vectorCount, dst, ptr, access = line.args

            declaration, declerationLine = ptx_shader.findDeclaration(dst)
            srcDeclaration, _ = ptx_shader.findDeclaration(ptr)
            
            # assert srcDeclaration.pointerVariableType == declaration.variableType

            # debug_print(line.fullLine)

            # assert srcDeclaration.pointerVariableType[:2] == '.b' or srcDeclaration.pointerVariableType[:2] == '.f'

            assert srcDeclaration.pointerVariableType[2:] == declaration.variableType[2:]
            declaration.buildString(declaration.declarationType, declaration.vector, srcDeclaration.pointerVariableType, declaration.variableName)

            # if ptr == '%ssa_13':
            #     debug_print(declaration.fullLine)
            #     exit(-1)

            
            # if srcDeclaration.pointerVariableType == None:
            #     exit(-1)

            if not declaration.isVector():
                line.buildString('ld.global%s' % (declaration.variableType), (dst, '[%s]' % ptr))
            else:
                newLines = list()

                # load into each register
                for i in range(declaration.vectorSize()):
                    if int(vectorCount) > 0 and i >= int(vectorCount):
                        break
                    newFunctional = PTXFunctionalLine()
                    newFunctional.leadingWhiteSpace = declaration.leadingWhiteSpace
                    # debug_print('#432 ' + declaration.fullLine)
                    newFunctional.buildString('ld.global%s' % declaration.variableType, (declaration.variableName + '_' + str(i), '[' + ptr + ' + ' + str(int(i * declaration.bitCount() / 8)) + ']'))
                    newLines.append(newFunctional)
                
                # insert the new lines into shader
                newLines.append(PTXLine('//' + line.comment + '\n'))
                ptx_shader.lines.remove(line)
                ptx_shader.lines[index: index] = newLines
        
        
        elif line.functionalType == FunctionalType.store_deref:
            # debug_print("################")
            # debug_print(line.fullLine)
            ptr, dst, wrmask, access = line.args
            # dst = line.args[1]
            # ptr = line.args[0]

            declaration, declerationLine = ptx_shader.findDeclaration(dst)
            if not declaration.isVector():
                line.buildString('st.global%s' % (declaration.variableType), ('[%s]' % ptr, dst))
            else:
                newLines = list()

                # load into each register
                for i in range(declaration.vectorSize()):
                    if int(wrmask) & (1 << i) == 0:
                        continue
                    newFunctional = PTXFunctionalLine()
                    newFunctional.leadingWhiteSpace = declaration.leadingWhiteSpace
                    newFunctional.buildString('st.global%s' % declaration.variableType, ('[' + ptr  + ' + ' + str(int(i * declaration.bitCount() / 8)) + ']', declaration.variableName + '_' + str(i)))
                    newLines.append(newFunctional)
                
                # insert the new lines into shader
                ptx_shader.lines.remove(line)
                newLines.append(PTXLine('//' + line.comment + '\n'))
                ptx_shader.lines[index: index] = newLines
        

        elif line.functionalType == FunctionalType.deref_var:
            dst, src, baseType, type = line.args
            
            declaration, declerationLine = ptx_shader.findDeclaration(dst)
            assert not declaration.isVector()
            assert declaration.declarationType == DeclarationType.Register
            declaration.buildString(DeclarationType.Register, None, '.b64', declaration.variableName)
            declaration.pointerVariableType = '.' + baseType

            line.buildString('mov.b64', (dst, '%' + src))


        # elif line.functionalType == FunctionalType.mov:
        #     debug_print(line.fullLine)
        #     debug_print(line.args)
        #     #assert len(line.args) == 2
        #     if '.' in line.args[0]: #TODO: args with brackets are parsed incorrectly
        #         if line.vector == None:
        #             variableType = line.variableType
        #             debug_print(line.fullLine)
        #             debug_print(variableType)
        #             #exit(-1)
        #             if variableType == '.b32':
        #                 variableType = '.f32'
        #             elif variableType == '.b64':
        #                 variableType = '.f64'
        #             zero = '0'
        #             if variableType[1] == 'f':
        #                 zero = '0F00000000'
        #             line.buildString('add%s' % variableType, (line.args[0], line.args[1], zero))

def translate_trace_ray(ptx_shader, shaderIDs):
    trace_ray_ID = 0
    skip_lines = -1
    for index in range(len(ptx_shader.lines)):
        if index <= skip_lines:
            continue
        line = ptx_shader.lines[index]
        debug_print(line)
        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.functionalType != FunctionalType.trace_ray:
            continue

        assert len(line.args) == 11


        traversal_finished_reg = '%traversal_finished_' + str(trace_ray_ID)
        traversal_finished_declaration = PTXDecleration()
        traversal_finished_declaration.leadingWhiteSpace = line.leadingWhiteSpace
        traversal_finished_declaration.buildString(DeclarationType.Register, None, '.u32', traversal_finished_reg)

        symbolic_rt_submit = rtcore_symbolic_submit_enabled()
        v04_shadow_publication = rtcore_v04_shadow_publication_enabled()
        trace_submit_setup = []

        topLevelAS, rayFlags, cullMask, sbtRecordOffset, sbtRecordStride, missIndex, origin, Tmin, direction, Tmax, payload = line.args
        line.args = line.args[:-1] # MRS_TODO: why there is a payload (in glsl code it is NULL but translated to ssa_88)? and why it gets an error to run?
        args = line.args

        # originRegNames, originDeclarations, originMovs, _ = unwrapp_vector(ptx_shader, origin, "trace_ray_" + str(index) + "_origin")
        # directionRegNames, directionDeclarations, directionMovs, _ = unwrapp_vector(ptx_shader, direction, "trace_ray_" + str(index) + "_direction")

        originRegNames = [origin + '_' + str(i) for i in range(3)]
        directionRegNames = [direction + '_' + str(i) for i in range(3)]

        args[8:9] = directionRegNames[:3]
        args[6:7] = originRegNames[:3]
        args.append(traversal_finished_reg)
        trace_ray_condition = line.condition
        trace_ray_lines = [line]
        continuation_anchor_lines = []
        if symbolic_rt_submit:
            if trace_ray_ID >= RTCORE_MAX_TRACE_SITES:
                rtcore_raise_compiler_lowering_contract_violation(
                    'trace-ray site exceeds bounded compact context arenas'
                )
            context_ptr_reg = '%rt_context_ptr_' + str(trace_ray_ID)
            context_base_reg = '%rt_context_base_' + str(trace_ray_ID)
            context_lane_offset_reg = '%rt_context_lane_offset_' + str(trace_ray_ID)
            launch_id_vector_reg = '%rt_launch_id_vec_' + str(trace_ray_ID)
            launch_size_vector_reg = '%rt_launch_size_vec_' + str(trace_ray_ID)
            launch_id_regs = [
                launch_id_vector_reg + '_' + str(component)
                for component in range(3)
            ]
            launch_size_regs = [
                launch_size_vector_reg + '_' + str(component)
                for component in range(3)
            ]
            lane_slot_reg = '%rt_lane_slot_' + str(trace_ray_ID)
            launch_yz_index_reg = '%rt_launch_yz_index_' + str(trace_ray_ID)
            context_index_reg = '%rt_context_index_' + str(trace_ray_ID)
            launch_width_rounded_reg = '%rt_launch_width_rounded_' + str(trace_ray_ID)
            warps_per_row_reg = '%rt_warps_per_row_' + str(trace_ray_ID)
            launch_x_warp_index_reg = '%rt_launch_x_warp_index_' + str(trace_ray_ID)
            global_warp_index_reg = '%rt_global_warp_index_' + str(trace_ray_ID)
            handoff_window_index_reg = '%rt_handoff_window_index_' + str(trace_ray_ID)
            handoff_window_offset_reg = '%rt_handoff_window_offset_' + str(trace_ray_ID)
            handoff_window_base_reg = '%rt_handoff_window_base_' + str(trace_ray_ID)
            continuation_lane_offset_reg = '%rt_continuation_lane_offset_' + str(trace_ray_ID)
            continuation_lane_ptr_reg = '%rt_continuation_lane_ptr_' + str(trace_ray_ID)
            previous_active_mask_reg = '%rt_previous_active_mask_' + str(trace_ray_ID)

            preflight_marker = rtcore_dispatch_descriptor_v0_preflight_marker(
                trace_ray_ID,
                line.leadingWhiteSpace,
            )
            descriptor_marker = rtcore_dispatch_descriptor_v0_marker(
                trace_ray_ID,
                line.leadingWhiteSpace,
            )
            custom_abi_evidence_marker = rtcore_custom_abi_lowering_evidence_marker(
                trace_ray_ID,
                line.leadingWhiteSpace,
            )
            context_field_address_plan_marker = (
                rtcore_context_v03_field_address_plan_marker(
                    line.leadingWhiteSpace,
                )
            )

            context_base_declaration = PTXDecleration()
            context_base_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            context_base_declaration.buildString(DeclarationType.Register, None, '.b64', context_base_reg)

            context_lane_offset_declaration = PTXDecleration()
            context_lane_offset_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            context_lane_offset_declaration.buildString(DeclarationType.Register, None, '.b64', context_lane_offset_reg)

            global_index_declarations = []
            for global_index_reg in (
                    lane_slot_reg,
                    launch_yz_index_reg,
                    context_index_reg,
                    launch_width_rounded_reg,
                    warps_per_row_reg,
                    launch_x_warp_index_reg,
                    global_warp_index_reg,
                    handoff_window_index_reg,
            ):
                declaration = PTXDecleration()
                declaration.leadingWhiteSpace = line.leadingWhiteSpace
                declaration.buildString(
                    DeclarationType.Register,
                    None,
                    '.u32',
                    global_index_reg,
                )
                global_index_declarations.append(declaration)

            launch_vector_declarations = []
            for launch_vector_reg in (
                launch_id_vector_reg,
                launch_size_vector_reg,
            ):
                declaration = PTXDecleration()
                declaration.leadingWhiteSpace = line.leadingWhiteSpace
                declaration.buildString(
                    DeclarationType.Register,
                    '.v4',
                    '.u32',
                    launch_vector_reg,
                )
                launch_vector_declarations.append(declaration)

            handoff_window_offset_declaration = PTXDecleration()
            handoff_window_offset_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            handoff_window_offset_declaration.buildString(
                DeclarationType.Register,
                None,
                '.b64',
                handoff_window_offset_reg,
            )

            context_ptr_declaration = PTXDecleration()
            context_ptr_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            context_ptr_declaration.buildString(DeclarationType.Register, None, '.b64', context_ptr_reg)

            handoff_window_base_declaration = PTXDecleration()
            handoff_window_base_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            handoff_window_base_declaration.buildString(DeclarationType.Register, None, '.b64', handoff_window_base_reg)

            context_base_init = PTXFunctionalLine()
            context_base_init.leadingWhiteSpace = line.leadingWhiteSpace
            context_base_init.buildString('mov.b64', (context_base_reg, rtcore_dispatch_descriptor_v0_context_base(trace_ray_ID)))

            launch_id_init = PTXFunctionalLine()
            launch_id_init.leadingWhiteSpace = line.leadingWhiteSpace
            launch_id_init.buildString(
                FunctionalType.load_ray_launch_id,
                (launch_id_vector_reg,),
            )

            launch_size_init = PTXFunctionalLine()
            launch_size_init.leadingWhiteSpace = line.leadingWhiteSpace
            launch_size_init.buildString(
                FunctionalType.load_ray_launch_size,
                (launch_size_vector_reg,),
            )

            launch_yz_index_init = PTXFunctionalLine()
            launch_yz_index_init.leadingWhiteSpace = line.leadingWhiteSpace
            launch_yz_index_init.buildString(
                'mad.lo.u32',
                (
                    launch_yz_index_reg,
                    launch_id_regs[2],
                    launch_size_regs[1],
                    launch_id_regs[1],
                ),
            )

            handoff_window_base_init = PTXFunctionalLine()
            handoff_window_base_init.leadingWhiteSpace = line.leadingWhiteSpace
            handoff_window_base_init.buildString('mov.b64', (handoff_window_base_reg, rtcore_dispatch_descriptor_v0_handoff_window_base(trace_ray_ID)))

            launch_width_rounded_init = PTXFunctionalLine()
            launch_width_rounded_init.leadingWhiteSpace = line.leadingWhiteSpace
            launch_width_rounded_init.buildString(
                'add.u32',
                (launch_width_rounded_reg, launch_size_regs[0], '31'),
            )

            warps_per_row_init = PTXFunctionalLine()
            warps_per_row_init.leadingWhiteSpace = line.leadingWhiteSpace
            warps_per_row_init.buildString(
                'shr.u32',
                (warps_per_row_reg, launch_width_rounded_reg, '5'),
            )

            launch_x_warp_index_init = PTXFunctionalLine()
            launch_x_warp_index_init.leadingWhiteSpace = line.leadingWhiteSpace
            launch_x_warp_index_init.buildString(
                'shr.u32',
                (launch_x_warp_index_reg, launch_id_regs[0], '5'),
            )

            global_warp_index_init = PTXFunctionalLine()
            global_warp_index_init.leadingWhiteSpace = line.leadingWhiteSpace
            global_warp_index_init.buildString(
                'mad.lo.u32',
                (
                    global_warp_index_reg,
                    launch_yz_index_reg,
                    warps_per_row_reg,
                    launch_x_warp_index_reg,
                ),
            )

            lane_slot_init = PTXFunctionalLine()
            lane_slot_init.leadingWhiteSpace = line.leadingWhiteSpace
            lane_slot_init.buildString(
                'and.b32',
                (lane_slot_reg, launch_id_regs[0], '31'),
            )

            context_index_init = PTXFunctionalLine()
            context_index_init.leadingWhiteSpace = line.leadingWhiteSpace
            context_index_init.buildString(
                'mad.lo.u32',
                (
                    context_index_reg,
                    global_warp_index_reg,
                    str(RTCORE_MAX_LANES_PER_WARP),
                    lane_slot_reg,
                ),
            )

            context_trace_site_index_init = PTXFunctionalLine()
            context_trace_site_index_init.leadingWhiteSpace = line.leadingWhiteSpace
            context_trace_site_index_init.buildString(
                'add.u32',
                (
                    context_index_reg,
                    context_index_reg,
                    str(trace_ray_ID * RTCORE_MAX_CONTEXTS_PER_TRACE_SITE),
                ),
            )

            context_lane_offset_init = PTXFunctionalLine()
            context_lane_offset_init.leadingWhiteSpace = line.leadingWhiteSpace
            context_lane_offset_init.buildString('mul.wide.u32', (context_lane_offset_reg, context_index_reg, str(RTCORE_CONTEXT_BYTES)))

            context_ptr_init = PTXFunctionalLine()
            context_ptr_init.leadingWhiteSpace = line.leadingWhiteSpace
            context_ptr_init.buildString('add.u64', (context_ptr_reg, context_base_reg, context_lane_offset_reg))

            handoff_window_index_init = PTXFunctionalLine()
            handoff_window_index_init.leadingWhiteSpace = line.leadingWhiteSpace
            handoff_window_index_init.buildString(
                'add.u32',
                (
                    handoff_window_index_reg,
                    global_warp_index_reg,
                    str(trace_ray_ID * RTCORE_MAX_WINDOWS_PER_TRACE_SITE),
                ),
            )

            handoff_window_offset_init = PTXFunctionalLine()
            handoff_window_offset_init.leadingWhiteSpace = line.leadingWhiteSpace
            handoff_window_offset_init.buildString(
                'mul.wide.u32',
                (
                    handoff_window_offset_reg,
                    handoff_window_index_reg,
                    str(RTCORE_HANDOFF_WINDOW_WARP_BYTES),
                ),
            )

            handoff_window_base_add = PTXFunctionalLine()
            handoff_window_base_add.leadingWhiteSpace = line.leadingWhiteSpace
            handoff_window_base_add.buildString(
                'add.u64',
                (
                    handoff_window_base_reg,
                    handoff_window_base_reg,
                    handoff_window_offset_reg,
                ),
            )

            continuation_setup = [
                PTXLine.createNewLine(
                    line.leadingWhiteSpace + '.reg .b64 ' +
                    continuation_lane_offset_reg + ';\n'
                ),
                PTXLine.createNewLine(
                    line.leadingWhiteSpace + '.reg .b64 ' +
                    continuation_lane_ptr_reg + ';\n'
                ),
                PTXLine.createNewLine(
                    line.leadingWhiteSpace + '.reg .u32 ' +
                    previous_active_mask_reg + ';\n'
                ),
                PTXLine.createNewLine(
                    line.leadingWhiteSpace + 'mul.wide.u32 ' +
                    continuation_lane_offset_reg + ', ' + lane_slot_reg +
                    ', ' + str(RTCORE_HANDOFF_WINDOW_SLOT_BYTES) + ';\n'
                ),
                PTXLine.createNewLine(
                    line.leadingWhiteSpace + 'add.u64 ' +
                    continuation_lane_ptr_reg + ', ' +
                    handoff_window_base_reg + ', ' +
                    continuation_lane_offset_reg + ';\n'
                ),
                PTXLine.createNewLine(
                    line.leadingWhiteSpace + 'activemask.b32 ' +
                    previous_active_mask_reg + ';\n'
                ),
            ]

            trace_submit_setup = [
                preflight_marker,
                descriptor_marker,
                custom_abi_evidence_marker,
                context_field_address_plan_marker,
                context_base_declaration,
                context_lane_offset_declaration,
            ] + launch_vector_declarations + global_index_declarations + [
                handoff_window_offset_declaration,
                context_ptr_declaration,
                handoff_window_base_declaration,
                context_base_init,
                launch_id_init,
                launch_size_init,
                launch_yz_index_init,
                handoff_window_base_init,
                launch_width_rounded_init,
                warps_per_row_init,
                launch_x_warp_index_init,
                global_warp_index_init,
                lane_slot_init,
                context_index_init,
                context_trace_site_index_init,
                context_lane_offset_init,
                context_ptr_init,
                handoff_window_index_init,
                handoff_window_offset_init,
                handoff_window_base_add,
            ] + continuation_setup
            v04_shadow_trace_input_lines = []
            if v04_shadow_publication:
                v04_shadow_trace_input_lines = (
                    rtcore_v04_shadow_trace_input_publication_lines(
                        line.leadingWhiteSpace,
                        trace_ray_condition,
                        trace_ray_ID,
                        continuation_lane_ptr_reg,
                        context_ptr_reg,
                        topLevelAS,
                        rayFlags,
                        cullMask,
                        sbtRecordOffset,
                        sbtRecordStride,
                        missIndex,
                        originRegNames,
                        Tmin,
                        directionRegNames,
                        Tmax,
                    )
                )
            trace_ray_line = None

            rt_submit_line = PTXFunctionalLine()
            rt_submit_line.leadingWhiteSpace = line.leadingWhiteSpace
            rt_submit_line.buildString(
                FunctionalType.rt_submit,
                (traversal_finished_reg, context_ptr_reg, handoff_window_base_reg),
            )
            rt_publish_trace_context_line = None
            trace_ray_lines = [rt_submit_line]
            if rtcore_compiler_driver_publication_source_enabled():
                rt_publish_trace_context_line = PTXFunctionalLine()
                rt_publish_trace_context_line.leadingWhiteSpace = line.leadingWhiteSpace
                rt_publish_trace_context_args = (
                    context_ptr_reg,
                    handoff_window_base_reg,
                    topLevelAS,
                    rayFlags,
                    cullMask,
                    sbtRecordOffset,
                    sbtRecordStride,
                    missIndex,
                    originRegNames[0],
                    originRegNames[1],
                    originRegNames[2],
                    Tmin,
                    directionRegNames[0],
                    directionRegNames[1],
                    directionRegNames[2],
                    Tmax,
                )
                if v04_shadow_publication:
                    rt_publish_trace_context_args += (
                        str(rtcore_abi_v04.LANE_SLOT_BYTES),
                    )
                rt_publish_trace_context_line.buildString(
                    FunctionalType.rt_publish_trace_context,
                    rt_publish_trace_context_args,
                )
                trace_ray_lines = (
                    [rt_publish_trace_context_line] +
                    v04_shadow_trace_input_lines +
                    [rt_submit_line]
                )
            rtcore_copy_trace_ray_condition(
                trace_ray_condition,
                trace_ray_line=trace_ray_line,
                rt_submit_line=rt_submit_line,
                rt_publish_trace_context_line=rt_publish_trace_context_line,
            )
            rtcore_validate_trace_ray_compiler_contract(
                trace_ray_line,
                rt_submit_line,
                rt_publish_trace_context_line,
                context_ptr_reg,
                handoff_window_base_reg,
                v04_shadow_publication,
            )
            continuation_anchor_label_str = (
                'rt_continuation_anchor_' + str(trace_ray_ID)
            )
            continuation_anchor_branch = PTXFunctionalLine()
            continuation_anchor_branch.leadingWhiteSpace = line.leadingWhiteSpace
            continuation_anchor_branch.buildString(
                FunctionalType.bra, (continuation_anchor_label_str,)
            )
            continuation_anchor_label = PTXLine('')
            continuation_anchor_label.fullLine = (
                line.leadingWhiteSpace + continuation_anchor_label_str + ':\n'
            )
            continuation_suffix = str(trace_ray_ID)
            continuation_registers = [
                ('u32', '%rt_shader_hit_result_' + continuation_suffix),
                ('u32', '%rt_return_reason_' + continuation_suffix),
                ('u32', '%rt_completion_valid_word_' + continuation_suffix),
                ('u32', '%rt_next_active_mask_' + continuation_suffix),
                ('u32', '%rt_masked_next_active_mask_' + continuation_suffix),
            ]
            continuation_predicates = [
                '%rt_completion_valid_' + continuation_suffix,
                '%rt_reason_miss_' + continuation_suffix,
                '%rt_reason_closest_hit_' + continuation_suffix,
                '%rt_reason_anyhit_' + continuation_suffix,
                '%rt_reason_intersection_' + continuation_suffix,
                '%rt_reason_continuation_' + continuation_suffix,
                '%rt_reason_terminal_shader_' + continuation_suffix,
                '%rt_anyhit_accept_' + continuation_suffix,
                '%rt_anyhit_ignore_' + continuation_suffix,
                '%rt_anyhit_result_valid_' + continuation_suffix,
                '%rt_intersection_none_' + continuation_suffix,
                '%rt_intersection_reported_' + continuation_suffix,
                '%rt_intersection_result_valid_' + continuation_suffix,
                '%rt_anyhit_resume_' + continuation_suffix,
                '%rt_intersection_resume_' + continuation_suffix,
                '%rt_should_resubmit_' + continuation_suffix,
                '%rt_next_mask_subset_' + continuation_suffix,
                '%rt_guarded_resubmit_' + continuation_suffix,
                '%rt_publication_dirty_' + continuation_suffix,
                '%rt_round_publication_dirty_' + continuation_suffix,
            ]
            continuation_declarations = [
                PTXLine.createNewLine(
                    line.leadingWhiteSpace + '.reg .' + register_type + ' ' +
                    register_name + ';\n'
                )
                for register_type, register_name in continuation_registers
            ] + [
                PTXLine.createNewLine(
                    line.leadingWhiteSpace + '.reg .pred ' + predicate + ';\n'
                )
                for predicate in continuation_predicates
            ]
            hit_result_reg = '%rt_shader_hit_result_' + continuation_suffix
            return_reason_reg = '%rt_return_reason_' + continuation_suffix
            completion_word_reg = '%rt_completion_valid_word_' + continuation_suffix
            next_active_mask_reg = '%rt_next_active_mask_' + continuation_suffix
            masked_next_active_mask_reg = (
                '%rt_masked_next_active_mask_' + continuation_suffix
            )
            completion_valid_pred = '%rt_completion_valid_' + continuation_suffix
            miss_reason_pred = '%rt_reason_miss_' + continuation_suffix
            closest_hit_reason_pred = '%rt_reason_closest_hit_' + continuation_suffix
            anyhit_reason_pred = '%rt_reason_anyhit_' + continuation_suffix
            intersection_reason_pred = '%rt_reason_intersection_' + continuation_suffix
            continuation_reason_pred = '%rt_reason_continuation_' + continuation_suffix
            terminal_shader_reason_pred = (
                '%rt_reason_terminal_shader_' + continuation_suffix
            )
            anyhit_accept_pred = '%rt_anyhit_accept_' + continuation_suffix
            anyhit_ignore_pred = '%rt_anyhit_ignore_' + continuation_suffix
            anyhit_valid_pred = '%rt_anyhit_result_valid_' + continuation_suffix
            intersection_none_pred = '%rt_intersection_none_' + continuation_suffix
            intersection_reported_pred = '%rt_intersection_reported_' + continuation_suffix
            intersection_valid_pred = '%rt_intersection_result_valid_' + continuation_suffix
            anyhit_resume_pred = '%rt_anyhit_resume_' + continuation_suffix
            intersection_resume_pred = '%rt_intersection_resume_' + continuation_suffix
            should_resubmit_pred = '%rt_should_resubmit_' + continuation_suffix
            subset_pred = '%rt_next_mask_subset_' + continuation_suffix
            guarded_resubmit_pred = '%rt_guarded_resubmit_' + continuation_suffix
            publication_dirty_pred = '%rt_publication_dirty_' + continuation_suffix
            round_dirty_pred = '%rt_round_publication_dirty_' + continuation_suffix
            fence_done_label = 'rt_continuation_fence_done_' + continuation_suffix
            resubmit_label = 'rt_continuation_resubmit_' + continuation_suffix
            final_wait_label = 'rt_continuation_final_wait_' + continuation_suffix
            continuation_body_text = [
                'mov.u32 %s, 0;' % hit_result_reg,
                'and.b32 %s, %s, 255;' % (return_reason_reg, traversal_finished_reg),
                'and.b32 %s, %s, 2147483648;' % (
                    completion_word_reg, traversal_finished_reg),
                'setp.ne.u32 %s, %s, 0;' % (
                    completion_valid_pred, completion_word_reg),
                'setp.eq.u32 %s, %s, 1;' % (
                    miss_reason_pred, return_reason_reg),
                'setp.eq.u32 %s, %s, 2;' % (
                    closest_hit_reason_pred, return_reason_reg),
                'setp.eq.u32 %s, %s, 3;' % (
                    anyhit_reason_pred, return_reason_reg),
                'setp.eq.u32 %s, %s, 4;' % (
                    intersection_reason_pred, return_reason_reg),
                'or.pred %s, %s, %s;' % (
                    continuation_reason_pred, anyhit_reason_pred,
                    intersection_reason_pred),
                'or.pred %s, %s, %s;' % (
                    terminal_shader_reason_pred, miss_reason_pred,
                    closest_hit_reason_pred),
                '@%s ld.global.u32 %s, [%s + 52];' % (
                    continuation_reason_pred, hit_result_reg,
                    continuation_lane_ptr_reg),
                'setp.eq.u32 %s, %s, 2;' % (
                    anyhit_accept_pred, hit_result_reg),
                'setp.eq.u32 %s, %s, 3;' % (
                    anyhit_ignore_pred, hit_result_reg),
                'or.pred %s, %s, %s;' % (
                    anyhit_valid_pred, anyhit_accept_pred,
                    anyhit_ignore_pred),
                'setp.eq.u32 %s, %s, 1;' % (
                    intersection_none_pred, hit_result_reg),
                'setp.eq.u32 %s, %s, 4;' % (
                    intersection_reported_pred, hit_result_reg),
                'or.pred %s, %s, %s;' % (
                    intersection_valid_pred, intersection_none_pred,
                    intersection_reported_pred),
                'and.pred %s, %s, %s;' % (
                    anyhit_resume_pred, anyhit_reason_pred,
                    anyhit_valid_pred),
                'and.pred %s, %s, %s;' % (
                    intersection_resume_pred, intersection_reason_pred,
                    intersection_valid_pred),
                'or.pred %s, %s, %s;' % (
                    should_resubmit_pred, anyhit_resume_pred,
                    intersection_resume_pred),
                'and.pred %s, %s, %s;' % (
                    should_resubmit_pred, should_resubmit_pred,
                    completion_valid_pred),
                'vote.sync.ballot.b32 %s, %s, %s;' % (
                    next_active_mask_reg, should_resubmit_pred,
                    previous_active_mask_reg),
                'and.b32 %s, %s, %s;' % (
                    masked_next_active_mask_reg, next_active_mask_reg,
                    previous_active_mask_reg),
                'setp.eq.u32 %s, %s, %s;' % (
                    subset_pred, masked_next_active_mask_reg,
                    next_active_mask_reg),
                'and.pred %s, %s, %s;' % (
                    guarded_resubmit_pred, should_resubmit_pred,
                    subset_pred),
                'or.pred %s, %s, %s;' % (
                    publication_dirty_pred, continuation_reason_pred,
                    terminal_shader_reason_pred),
                'vote.sync.any.pred %s, %s, %s;' % (
                    round_dirty_pred, publication_dirty_pred,
                    previous_active_mask_reg),
                '@!%s bra %s;' % (round_dirty_pred, fence_done_label),
                'membar.gl;',
                fence_done_label + ':',
                '@%s bra %s;' % (guarded_resubmit_pred, resubmit_label),
                'bra %s;' % final_wait_label,
                resubmit_label + ':',
                'mov.b32 %s, %s;' % (
                    previous_active_mask_reg, next_active_mask_reg),
                'rt_submit %s, %s, %s;' % (
                    traversal_finished_reg, context_ptr_reg,
                    handoff_window_base_reg),
                'bra %s;' % continuation_anchor_label_str,
                final_wait_label + ':',
            ]
            continuation_body = []
            for continuation_line in continuation_body_text:
                if continuation_line.endswith(':'):
                    label_line = PTXLine('')
                    label_line.fullLine = (
                        line.leadingWhiteSpace + continuation_line + '\n'
                    )
                    continuation_body.append(label_line)
                else:
                    condition = ''
                    instruction_text = continuation_line
                    if continuation_line.startswith('@'):
                        condition, instruction_text = continuation_line.split(
                            None, 1
                        )
                    instruction_line = PTXLine.createNewLine(
                        line.leadingWhiteSpace + instruction_text + '\n'
                    )
                    if condition:
                        instruction_line.condition = condition
                        instruction_line.buildString(
                            instruction_line.fullFunction,
                            instruction_line.args,
                        )
                    continuation_body.append(instruction_line)
            continuation_anchor_lines = [
                continuation_anchor_branch,
                continuation_anchor_label,
            ] + continuation_declarations + continuation_body
        else:
            line.buildString(line.functionalType, args)

        
        #intersection shaders
        intersection_lines = []
        anyhit_lines = []

        if ShaderType.Intersection in shaderIDs and ShaderType.Any_hit in shaderIDs:
            print("Combined intersection and anyhit shader currently unimplemented! Results may be incorrect!")

        if ShaderType.Intersection in shaderIDs:

            intersection_counter_reg = '%intersection_counter_' + str(trace_ray_ID)
            intersection_counter_declaration = PTXDecleration()
            intersection_counter_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            intersection_counter_declaration.buildString(DeclarationType.Register, None, '.u32', intersection_counter_reg)
            intersection_lines.append(intersection_counter_declaration)

            intersection_counter_mov = PTXFunctionalLine()
            intersection_counter_mov.leadingWhiteSpace = line.leadingWhiteSpace
            intersection_counter_mov.buildString('mov.u32', (intersection_counter_reg, '0'))
            intersection_lines.append(intersection_counter_mov)

            intersection_loop_label_str = 'intersection_loop_' + str(trace_ray_ID)
            intersection_loop_label = PTXLine('')
            intersection_loop_label.fullLine = line.leadingWhiteSpace + intersection_loop_label_str + ':\n'
            intersection_lines.append(intersection_loop_label)

            intersection_exit_reg = '%intersections_exit_' + str(trace_ray_ID)
            intersection_exit_declaration = PTXDecleration()
            intersection_exit_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            intersection_exit_declaration.buildString(DeclarationType.Register, None, '.pred', intersection_exit_reg)
            intersection_lines.append(intersection_exit_declaration)

            intersection_exit = PTXFunctionalLine()
            intersection_exit.leadingWhiteSpace = line.leadingWhiteSpace
            intersection_exit.buildString('intersection_exit.pred', (intersection_exit_reg, intersection_counter_reg, traversal_finished_reg))
            intersection_lines.append(intersection_exit)

            exit_intersection_label_str = 'exit_intersection_label_' + str(trace_ray_ID)
            exit_intersection_bra = PTXFunctionalLine()
            exit_intersection_bra.leadingWhiteSpace = line.leadingWhiteSpace
            exit_intersection_bra.condition = '@' + intersection_exit_reg
            exit_intersection_bra.buildString(FunctionalType.bra, (exit_intersection_label_str, ))
            intersection_lines.append(exit_intersection_bra)

            shader_data_address_reg = '%shader_data_address_' + str(trace_ray_ID)
            shader_data_address_declaration = PTXDecleration()
            shader_data_address_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            shader_data_address_declaration.buildString(DeclarationType.Register, None, '.b64', shader_data_address_reg)
            intersection_lines.append(shader_data_address_declaration)

            get_shader_data_address = PTXFunctionalLine()
            get_shader_data_address.leadingWhiteSpace = line.leadingWhiteSpace
            get_shader_data_address.buildString('get_intersection_shader_data_address', (shader_data_address_reg, intersection_counter_reg))
            intersection_lines.append(get_shader_data_address)


            if intersection_table_type == Intersection_Table_Type.FCC:
                run_intersection_reg = '%run_intersection_' + str(trace_ray_ID)
                run_intersection_declaration = PTXDecleration()
                run_intersection_declaration.leadingWhiteSpace = line.leadingWhiteSpace
                run_intersection_declaration.buildString(DeclarationType.Register, None, '.pred', run_intersection_reg)
                intersection_lines.append(run_intersection_declaration)

                run_intersection = PTXFunctionalLine()
                run_intersection.leadingWhiteSpace = line.leadingWhiteSpace
                run_intersection.buildString('run_intersection.pred', (run_intersection_reg, intersection_counter_reg, traversal_finished_reg))
                intersection_lines.append(run_intersection)

                skip_intersection_label_str = 'skip_intersection_label_' + str(trace_ray_ID)
                skip_intersection_bra = PTXFunctionalLine()
                skip_intersection_bra.leadingWhiteSpace = line.leadingWhiteSpace
                skip_intersection_bra.condition = '@!' + run_intersection_reg
                skip_intersection_bra.buildString(FunctionalType.bra, (skip_intersection_label_str, ))
                intersection_lines.append(skip_intersection_bra)

                primitiveID_reg = '%primitiveID_' + str(trace_ray_ID)
                primitiveID_declaration = PTXDecleration()
                primitiveID_declaration.leadingWhiteSpace = line.leadingWhiteSpace
                primitiveID_declaration.buildString(DeclarationType.Register, None, '.u32', primitiveID_reg)
                intersection_lines.append(primitiveID_declaration)

                primitiveID_load = PTXFunctionalLine()
                primitiveID_load.leadingWhiteSpace = line.leadingWhiteSpace
                primitiveID_load.buildString('ld.global.u32', (primitiveID_reg, '[' + shader_data_address_reg + ']'))
                intersection_lines.append(primitiveID_load)

                instanceID_reg = '%instanceID_' + str(trace_ray_ID)
                instanceID_declaration = PTXDecleration()
                instanceID_declaration.leadingWhiteSpace = line.leadingWhiteSpace
                instanceID_declaration.buildString(DeclarationType.Register, None, '.u32', instanceID_reg)
                intersection_lines.append(instanceID_declaration)

                instanceID_load = PTXFunctionalLine()
                instanceID_load.leadingWhiteSpace = line.leadingWhiteSpace
                instanceID_load.buildString('ld.global.u32', (instanceID_reg, '[' + shader_data_address_reg + ' + 4]'))
                intersection_lines.append(instanceID_load)

                call_intersection = PTXFunctionalLine()
                call_intersection.leadingWhiteSpace = line.leadingWhiteSpace
                call_intersection.buildString(FunctionalType.call_intersection_shader, (intersection_counter_reg, ))
                intersection_lines.append(call_intersection)

                skip_intersection_label = PTXLine('')
                skip_intersection_label.fullLine = line.leadingWhiteSpace + skip_intersection_label_str + ':\n'
                intersection_lines.append(skip_intersection_label)
            
            else: # baseline
                intersection_shaderID_reg = '%intersection_shaderID_' + str(trace_ray_ID)
                intersection_shaderID_declaration = PTXDecleration()
                intersection_shaderID_declaration.leadingWhiteSpace = line.leadingWhiteSpace
                intersection_shaderID_declaration.buildString(DeclarationType.Register, None, '.u32', intersection_shaderID_reg)
                intersection_lines.append(intersection_shaderID_declaration)

                get_intersection_shaderID = PTXFunctionalLine()
                get_intersection_shaderID.leadingWhiteSpace = line.leadingWhiteSpace
                get_intersection_shaderID.buildString(FunctionalType.get_intersection_shaderID, (intersection_shaderID_reg, intersection_counter_reg))
                intersection_lines.append(get_intersection_shaderID)

                for shaderID in shaderIDs[ShaderType.Intersection]:
                    skip_intersection_reg = '%skip_intersection_' + str(shaderID) + '_' + str(trace_ray_ID)
                    skip_intersection_declaration = PTXDecleration()
                    skip_intersection_declaration.leadingWhiteSpace = line.leadingWhiteSpace
                    skip_intersection_declaration.buildString(DeclarationType.Register, None, '.pred', skip_intersection_reg)
                    intersection_lines.append(skip_intersection_declaration)

                    skip_intersection_pred = PTXFunctionalLine()
                    skip_intersection_pred.leadingWhiteSpace = line.leadingWhiteSpace
                    skip_intersection_pred.buildString('setp.ne.u32', (skip_intersection_reg, intersection_shaderID_reg, str(shaderID)))
                    intersection_lines.append(skip_intersection_pred)

                    skip_intersection_label_str = 'skip_intersection_label_' + str(shaderID) + '_' + str(trace_ray_ID)
                    skip_intersection_bra = PTXFunctionalLine()
                    skip_intersection_bra.leadingWhiteSpace = line.leadingWhiteSpace
                    skip_intersection_bra.condition = '@' + skip_intersection_reg
                    skip_intersection_bra.buildString(FunctionalType.bra, (skip_intersection_label_str, ))
                    intersection_lines.append(skip_intersection_bra)

                    call_intersection = PTXFunctionalLine()
                    call_intersection.leadingWhiteSpace = line.leadingWhiteSpace
                    call_intersection.buildString(FunctionalType.call_intersection_shader, (intersection_counter_reg, ))
                    intersection_lines.append(call_intersection)

                    skip_intersection_label = PTXLine('')
                    skip_intersection_label.fullLine = line.leadingWhiteSpace + skip_intersection_label_str + ':\n'
                    intersection_lines.append(skip_intersection_label)

            intersection_counter_add = PTXFunctionalLine()
            intersection_counter_add.leadingWhiteSpace = line.leadingWhiteSpace
            intersection_counter_add.buildString('add.u32', (intersection_counter_reg, intersection_counter_reg, '1'))
            intersection_lines.append(intersection_counter_add)

            intersection_loop_bra = PTXFunctionalLine()
            intersection_loop_bra.leadingWhiteSpace = line.leadingWhiteSpace
            intersection_loop_bra.buildString(FunctionalType.bra, (intersection_loop_label_str, ))
            intersection_lines.append(intersection_loop_bra)

            exit_intersection_label = PTXLine('')
            exit_intersection_label.fullLine = line.leadingWhiteSpace + exit_intersection_label_str + ':\n'
            intersection_lines.append(exit_intersection_label)

        if symbolic_rt_submit:
            intersection_lines = []

        if ShaderType.Any_hit in shaderIDs:
            print("NIR-PTX Translator: Anyhit shader identified!")
            '''
            https://registry.khronos.org/vulkan/specs/1.3-extensions/html/chap9.html#shaders-any-hit
            The any-hit shader is executed after the intersection shader reports an intersection that lies within the current [tmin,tmax] of the ray. 
            The main use of any-hit shaders is to programmatically decide whether or not an intersection will be accepted. 
            The intersection will be accepted unless the shader calls the OpIgnoreIntersectionKHR instruction. 
            Any-hit shaders have read-only access to the attributes generated by the corresponding intersection shader, and can read or modify the ray payload.
            The order in which intersections are found along a ray, and therefore the order in which any-hit shaders are executed, is unspecified.
            The any-hit shader of the closest hit is guaranteed to be executed at some point during traversal, unless the ray is forcibly terminated.
            '''

            # For-loop counter to cycle through all hits
            # int i;
            anyhit_counter_reg = 'anyhit_counter_' + str(trace_ray_ID)
            anyhit_counter_declaration = PTXDecleration()
            anyhit_counter_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            anyhit_counter_declaration.buildString(DeclarationType.Register, None, '.u32', anyhit_counter_reg)
            anyhit_lines.append(anyhit_counter_declaration)

            # i = 0
            anyhit_counter_mov = PTXFunctionalLine()
            anyhit_counter_mov.leadingWhiteSpace = line.leadingWhiteSpace
            anyhit_counter_mov.buildString('mov.u32', (anyhit_counter_reg, '0'))
            anyhit_lines.append(anyhit_counter_mov)

            # loop label
            anyhit_loop_label_str = 'anyhit_loop_' + str(trace_ray_ID)
            anyhit_loop_label = PTXLine('')
            anyhit_loop_label.fullLine = line.leadingWhiteSpace + anyhit_loop_label_str + ':\n'
            anyhit_lines.append(anyhit_loop_label)

            # bool done
            anyhit_exit_reg = '%anyhit_exit_' + str(trace_ray_ID)
            anyhit_exit_declaration = PTXDecleration()
            anyhit_exit_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            anyhit_exit_declaration.buildString(DeclarationType.Register, None, '.pred', anyhit_exit_reg)
            anyhit_lines.append(anyhit_exit_declaration)

            # done = (i > n)
            anyhit_exit = PTXFunctionalLine()
            anyhit_exit.leadingWhiteSpace = line.leadingWhiteSpace
            anyhit_exit.buildString('anyhit_exit.pred', (anyhit_exit_reg, anyhit_counter_reg, traversal_finished_reg))
            anyhit_lines.append(anyhit_exit)

            # if done, jump to exit
            exit_anyhit_label_str = 'exit_anyhit_label_' + str(trace_ray_ID)
            exit_anyhit_bra = PTXFunctionalLine()
            exit_anyhit_bra.leadingWhiteSpace = line.leadingWhiteSpace
            exit_anyhit_bra.condition = '@' + anyhit_exit_reg
            exit_anyhit_bra.buildString(FunctionalType.bra, (exit_anyhit_label_str, ))
            anyhit_lines.append(exit_anyhit_bra)

            # function* anyhit_shader
            shader_data_address_reg = '%shader_data_address_any_' + str(trace_ray_ID)
            shader_data_address_declaration = PTXDecleration()
            shader_data_address_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            shader_data_address_declaration.buildString(DeclarationType.Register, None, '.b64', shader_data_address_reg)
            anyhit_lines.append(shader_data_address_declaration)

            # anyhit_shader = get_address()
            get_shader_data_address = PTXFunctionalLine()
            get_shader_data_address.leadingWhiteSpace = line.leadingWhiteSpace
            get_shader_data_address.buildString('get_anyhit_shader_data_address', (shader_data_address_reg, anyhit_counter_reg))
            anyhit_lines.append(get_shader_data_address)

            # unsigned shader_id
            anyhit_shaderID_reg = '%anyhit_shaderID_' + str(trace_ray_ID)
            anyhit_shaderID_declaration = PTXDecleration()
            anyhit_shaderID_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            anyhit_shaderID_declaration.buildString(DeclarationType.Register, None, '.u32', anyhit_shaderID_reg)
            anyhit_lines.append(anyhit_shaderID_declaration)

            # shader_id = get_ID()
            get_anyhit_shaderID = PTXFunctionalLine()
            get_anyhit_shaderID.leadingWhiteSpace = line.leadingWhiteSpace
            get_anyhit_shaderID.buildString(FunctionalType.get_anyhit_shaderID, (anyhit_shaderID_reg, anyhit_counter_reg))
            anyhit_lines.append(get_anyhit_shaderID)

            # Repeat for each defined any-hit shader
            for shaderID in shaderIDs[ShaderType.Any_hit]:

                # bool skip_shader
                skip_anyhit_reg = '%skip_anyhit_' + str(shaderID) + '_' + str(trace_ray_ID)
                skip_anyhit_declaration = PTXDecleration()
                skip_anyhit_declaration.leadingWhiteSpace = line.leadingWhiteSpace
                skip_anyhit_declaration.buildString(DeclarationType.Register, None, '.pred', skip_anyhit_reg)
                anyhit_lines.append(skip_anyhit_declaration)

                # skip_shader = (shader_id != ID)
                skip_anyhit_pred = PTXFunctionalLine()
                skip_anyhit_pred.leadingWhiteSpace = line.leadingWhiteSpace
                skip_anyhit_pred.buildString('setp.ne.u32', (skip_anyhit_reg, anyhit_shaderID_reg, str(shaderID)))
                anyhit_lines.append(skip_anyhit_pred)

                # if skip_shader, jump to next label
                skip_anyhit_label_str = 'skip_anyhit_label_' + str(shaderID) + '_' + str(trace_ray_ID)
                skip_anyhit_bra = PTXFunctionalLine()
                skip_anyhit_bra.leadingWhiteSpace = line.leadingWhiteSpace
                skip_anyhit_bra.condition = '@' + skip_anyhit_reg
                skip_anyhit_bra.buildString(FunctionalType.bra, (skip_anyhit_label_str, ))
                anyhit_lines.append(skip_anyhit_bra)

                # call shader
                call_anyhit = PTXFunctionalLine()
                call_anyhit.leadingWhiteSpace = line.leadingWhiteSpace
                call_anyhit.buildString(FunctionalType.call_anyhit_shader, (anyhit_counter_reg, ))
                anyhit_lines.append(call_anyhit)

                # skip label
                skip_anyhit_label = PTXLine('')
                skip_anyhit_label.fullLine = line.leadingWhiteSpace + skip_anyhit_label_str + ':\n'
                anyhit_lines.append(skip_anyhit_label)

            # i++
            anyhit_counter_add = PTXFunctionalLine()
            anyhit_counter_add.leadingWhiteSpace = line.leadingWhiteSpace
            anyhit_counter_add.buildString('add.u32', (anyhit_counter_reg, anyhit_counter_reg, '1'))
            anyhit_lines.append(anyhit_counter_add)

            # loop
            anyhit_loop_bra = PTXFunctionalLine()
            anyhit_loop_bra.leadingWhiteSpace = line.leadingWhiteSpace
            anyhit_loop_bra.buildString(FunctionalType.bra, (anyhit_loop_label_str, ))
            anyhit_lines.append(anyhit_loop_bra)

            # exit label
            exit_anyhit_label = PTXLine('')
            exit_anyhit_label.fullLine = line.leadingWhiteSpace + exit_anyhit_label_str + ':\n'
            anyhit_lines.append(exit_anyhit_label)

        if symbolic_rt_submit:
            anyhit_lines = []

        # get hit_geometry
        hit_geometry_reg = '%hit_geometry_' + str(trace_ray_ID)
        hit_geometry_declaration = PTXDecleration()
        hit_geometry_declaration.leadingWhiteSpace = line.leadingWhiteSpace
        hit_geometry_declaration.buildString(DeclarationType.Register, None, '.pred', hit_geometry_reg)

        hit_geometry = PTXFunctionalLine()
        hit_geometry.leadingWhiteSpace = line.leadingWhiteSpace
        hit_geometry.buildString('hit_geometry.pred', (hit_geometry_reg, traversal_finished_reg))

        # closest hit shader
        closest_hit_lines = []

        exit_closest_hit_label_str = 'exit_closest_hit_label_' + str(trace_ray_ID)
        call_closest_hit_bra = PTXFunctionalLine()
        call_closest_hit_bra.leadingWhiteSpace = line.leadingWhiteSpace
        call_closest_hit_bra.condition = '@!' + hit_geometry_reg
        call_closest_hit_bra.buildString(FunctionalType.bra, (exit_closest_hit_label_str, ))
        closest_hit_lines.append(call_closest_hit_bra)

        closest_hit_shaderID_reg = '%closest_hit_shaderID_' + str(trace_ray_ID)
        closest_hit_shaderID_declaration = PTXDecleration()
        closest_hit_shaderID_declaration.leadingWhiteSpace = line.leadingWhiteSpace
        closest_hit_shaderID_declaration.buildString(DeclarationType.Register, None, '.u32', closest_hit_shaderID_reg)
        closest_hit_lines.append(closest_hit_shaderID_declaration)

        get_closest_hit_shaderID = PTXFunctionalLine()
        get_closest_hit_shaderID.leadingWhiteSpace = line.leadingWhiteSpace
        get_closest_hit_shaderID.buildString(FunctionalType.get_closest_hit_shaderID, (closest_hit_shaderID_reg, ))
        closest_hit_lines.append(get_closest_hit_shaderID)

        for shaderID in shaderIDs.get(ShaderType.Closest_hit, []):
            skip_closest_hit_reg = '%skip_closest_hit_' + str(shaderID) + '_' + str(trace_ray_ID)
            skip_closest_hit_declaration = PTXDecleration()
            skip_closest_hit_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            skip_closest_hit_declaration.buildString(DeclarationType.Register, None, '.pred', skip_closest_hit_reg)
            closest_hit_lines.append(skip_closest_hit_declaration)

            skip_closest_hit_pred = PTXFunctionalLine()
            skip_closest_hit_pred.leadingWhiteSpace = line.leadingWhiteSpace
            skip_closest_hit_pred.buildString('setp.ne.u32', (skip_closest_hit_reg, closest_hit_shaderID_reg, str(shaderID)))
            closest_hit_lines.append(skip_closest_hit_pred)

            skip_closest_hit_label_str = 'skip_closest_hit_label_' + str(shaderID) + '_' + str(trace_ray_ID)
            skip_closest_hit_bra = PTXFunctionalLine()
            skip_closest_hit_bra.leadingWhiteSpace = line.leadingWhiteSpace
            skip_closest_hit_bra.condition = '@' + skip_closest_hit_reg
            skip_closest_hit_bra.buildString(FunctionalType.bra, (skip_closest_hit_label_str, ))
            closest_hit_lines.append(skip_closest_hit_bra)

            call_closest_hit = PTXFunctionalLine()
            call_closest_hit.leadingWhiteSpace = line.leadingWhiteSpace
            call_closest_hit.buildString(FunctionalType.call_closest_hit_shader, (str(shaderID), ))
            closest_hit_lines.append(call_closest_hit)

            skip_closest_hit_label = PTXLine('')
            skip_closest_hit_label.fullLine = line.leadingWhiteSpace + skip_closest_hit_label_str + ':\n'
            closest_hit_lines.append(skip_closest_hit_label)
        
        exit_closest_hit_label = PTXLine('')
        exit_closest_hit_label.fullLine = line.leadingWhiteSpace + exit_closest_hit_label_str + ':\n'
        closest_hit_lines.append(exit_closest_hit_label)

        # miss shader
        skip_miss_label_str = 'skip_miss_label_' + str(trace_ray_ID)
        call_miss_bra = PTXFunctionalLine()
        call_miss_bra.leadingWhiteSpace = line.leadingWhiteSpace
        call_miss_bra.condition = '@' + hit_geometry_reg
        call_miss_bra.buildString(FunctionalType.bra, (skip_miss_label_str, ))

        call_miss = PTXFunctionalLine()
        call_miss.leadingWhiteSpace = line.leadingWhiteSpace
        call_miss.buildString(FunctionalType.call_miss_shader, ())

        skip_miss_label = PTXLine('')
        skip_miss_label.fullLine = line.leadingWhiteSpace + skip_miss_label_str + ':\n'

        # finish trace ray
        end_trace_ray = PTXFunctionalLine()
        end_trace_ray.leadingWhiteSpace = line.leadingWhiteSpace
        end_trace_ray.buildString(FunctionalType.end_trace_ray, ())

        trace_retire = []
        if symbolic_rt_submit:
            retire_context = PTXFunctionalLine()
            retire_context.leadingWhiteSpace = line.leadingWhiteSpace
            retire_context.buildString(
                FunctionalType.rt_retire_context,
                (context_ptr_reg, handoff_window_base_reg),
            )
            rtcore_copy_trace_ray_condition(
                trace_ray_condition,
                retire_context=retire_context,
            )
            trace_retire.append(retire_context)

        terminal_final_dispatch_lines = []
        if symbolic_rt_submit:
            terminal_final_dispatch_authority = PTXLine('')
            terminal_final_dispatch_authority.fullLine = (
                line.leadingWhiteSpace
                + '// rtcore_terminal_final_dispatch '
                + 'authority=shadercore_direct legacy_final_shader_calls=0\n'
            )
            terminal_final_dispatch_lines.append(
                terminal_final_dispatch_authority
            )
        else:
            terminal_final_dispatch_lines.extend(
                [hit_geometry_declaration, hit_geometry, PTXLine('\n')]
            )
            terminal_final_dispatch_lines.extend(closest_hit_lines)
            terminal_final_dispatch_lines.append(PTXLine('\n'))
            terminal_final_dispatch_lines.extend(
                [call_miss_bra, call_miss, skip_miss_label, PTXLine('\n')]
            )
        terminal_final_dispatch_lines.append(end_trace_ray)

        newLines = [traversal_finished_declaration]
        newLines.extend(trace_submit_setup)
        newLines.extend(trace_ray_lines)
        newLines.extend(continuation_anchor_lines)
        newLines.append(PTXLine('\n'))
        newLines.extend(intersection_lines)
        newLines.append(PTXLine('\n'))
        newLines.extend(anyhit_lines)
        newLines.append(PTXLine('\n'))
        newLines.extend(terminal_final_dispatch_lines)
        newLines.extend(trace_retire)


        ptx_shader.lines[index:index + 1] = newLines
        
        skip_lines = index + len(newLines) - 1

        trace_ray_ID += 1



def translate_decl_var(ptx_shader):
    new_declerations = []
    old_declerations = []

    # newReg = PTXDecleration()
    # newReg.leadingWhiteSpace = '\t'
    # newReg.buildString(DeclarationType.Register, None, '.u32', '%allocasize')
    # new_declerations.append(newReg)


    for line in ptx_shader.lines:
        if line.instructionClass != InstructionClass.Functional:
            continue
        if line.functionalType != FunctionalType.decl_var:
            continue

        # debug_print(line.fullLine)
        # debug_print(line.args)
        # exit(-1)

        name, size, vector_number, variable_type, storage_qualifier_type, driver_location, binding = line.args
        name = '%' + name
        # if int(vector_number) > 1:
        #     continue

        newReg = PTXDecleration()
        newReg.leadingWhiteSpace = '\t'
        newReg.buildString(DeclarationType.Register, None, '.b64', name)

        if int(vector_number) != 0:
            allocation_size = int(size) * int(vector_number)
        else:
            allocation_size = int(size)


        # FIX: HARDCODED NUMBER
        if int(storage_qualifier_type) == 2 or int(storage_qualifier_type) == 16: ## uniform type
            newLine = PTXFunctionalLine()
            newLine.leadingWhiteSpace = '\t'
            newLine.comment = line.comment
            newLine.buildString('load_vulkan_descriptor', (name, driver_location, binding))
        else:
            newLine = PTXFunctionalLine()
            newLine.leadingWhiteSpace = '\t'
            newLine.comment = line.comment
            newLine.buildString('rt_alloc_mem', (name, str(allocation_size), str(storage_qualifier_type)))

        new_declerations.append(newReg)
        # new_declerations.append(newSizeSet)
        new_declerations.append(newLine)
        old_declerations.append(line)
    
    for decleration in old_declerations:
        ptx_shader.lines.remove(decleration)
    
    new_declerations.append(PTXLine('\n'))
    ptx_shader.addToStart(new_declerations)
    
    # for index in range(len(ptx_shader.lines)):
    #     line = ptx_shader.lines[index]
    #     if line.instructionClass != InstructionClass.EntryPoint:
    #         continue
    #     if 'main' not in line.fullLine:
    #         continue
        
    #     index += 1
    #     for decleration in new_declerations:
    #         ptx_shader.lines.insert(index + 1, decleration)
    #         index += 1
    #     break


def translate_load_GL_instructions(ptx_shader):
    skip_lines = -1
    for index in range(len(ptx_shader.lines)):
        if index <= skip_lines:
            continue
        line = ptx_shader.lines[index]
        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.functionalType == FunctionalType.load_ray_launch_id or line.functionalType == FunctionalType.load_ray_launch_size:
            dst = line.args[0]

            declaration, _ = ptx_shader.findDeclaration(dst)
            assert declaration.isVector()

            newRegNames = [(dst + '_' + str(i)) for i in range(4)]

            # newDeclarations = list()
            # for i in range(4):
            #     newDeclaration = PTXDecleration()
            #     newDeclaration.leadingWhiteSpace = line.leadingWhiteSpace
            #     newDeclaration.buildString(DeclarationType.Register, None, declaration.variableType, newRegNames[i])
            #     newDeclarations.append(newDeclaration)

            # comment = line.comment
            # line.comment = ""
            line.buildString(line.functionalType, (newRegNames[:3]))

            # loadZero = PTXFunctionalLine()
            # loadZero.leadingWhiteSpace = line.leadingWhiteSpace
            # loadZero.buildString('mov%s' % (declaration.variableType), (newRegNames[3], "0"))
            
            # _, _, _, wrapMovs = unwrapp_vector(ptx_shader, declaration.variableName, declaration.variableName)
            # movLine = PTXFunctionalLine()
            # movLine.leadingWhiteSpace = line.leadingWhiteSpace
            # movLine.comment = comment
            # movLine.buildString('mov%s%s' % (declaration.vector, declaration.variableType), (declaration.variableName, '{' + ", ".join(newRegNames) + '}'))

            # ptx_shader.lines[index:index] =  newDeclarations
            # ptx_shader.lines.insert(index + 5, loadZero)
            # ptx_shader.lines[index + 6: index + 6] = wrapMovs[:3]
            # skip_lines = index + 7
        
        
        elif line.functionalType == FunctionalType.load_ray_world_to_object or line.functionalType == FunctionalType.load_ray_object_to_world:
            dst, loadIndex = line.args

            newRegNames, _, _, _ = unwrapp_vector(ptx_shader, dst, dst)


            address_reg = str(dst) + '_address'
            address_declaration = PTXDecleration()
            address_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            address_declaration.buildString(DeclarationType.Register, None, '.b64', address_reg)

            offset = 0
            loads = []
            for regNames in newRegNames:
                newLoad = PTXFunctionalLine()
                newLoad.leadingWhiteSpace = line.leadingWhiteSpace
                newLoad.buildString('ld.global.f32', (regNames, '[' + address_reg + ' + ' + str(offset) + ']'))
                loads.append(newLoad)
                offset += 4

            line.buildString(line.functionalType, [address_reg, loadIndex, ])

            ptx_shader.lines[index:index + 1] = [address_declaration, line] + loads

            skip_lines = index + 2
        elif line.functionalType == FunctionalType.load_ray_world_direction:
            dst = line.args[0]

            address_reg = str(dst) + '_address'
            address_declaration = PTXDecleration()
            address_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            address_declaration.buildString(DeclarationType.Register, None, '.b64', address_reg)

            newRegNames, _, _, _ = unwrapp_vector(ptx_shader, dst, dst)

            offset = 0
            loads = []
            for regNames in newRegNames:
                newLoad = PTXFunctionalLine()
                newLoad.leadingWhiteSpace = line.leadingWhiteSpace
                newLoad.buildString('ld.global.f32', (regNames, '[' + address_reg + ' + ' + str(offset) + ']'))
                loads.append(newLoad)
                offset += 4

            line.buildString(line.functionalType, (address_reg, ))

            ptx_shader.lines[index:index + 1] = [address_declaration, line] + loads

            skip_lines = index + 2
        

        elif line.functionalType == FunctionalType.load_ray_world_origin:
            dst = line.args[0]

            address_reg = str(dst) + '_address'
            address_declaration = PTXDecleration()
            address_declaration.leadingWhiteSpace = line.leadingWhiteSpace
            address_declaration.buildString(DeclarationType.Register, None, '.b64', address_reg)

            newRegNames, _, _, _ = unwrapp_vector(ptx_shader, dst, dst)

            offset = 0
            loads = []
            for regNames in newRegNames:
                newLoad = PTXFunctionalLine()
                newLoad.leadingWhiteSpace = line.leadingWhiteSpace
                newLoad.buildString('ld.global.f32', (regNames, '[' + address_reg + ' + ' + str(offset) + ']'))
                loads.append(newLoad)
                offset += 4
            
            line.buildString(line.functionalType, (address_reg, ))

            ptx_shader.lines[index:index + 1] = [address_declaration, line] + loads

            skip_lines = index + 2







def translate_rt_shader_builtin_consumers(ptx_shader):
    if not rtcore_v04_shader_builtin_consumer_enabled():
        return

    for line in ptx_shader.lines:
        for _, opcode, display_name, _ in (
            RTCORE_V04_SUPPORTED_DIRECT_HIT_BUILTINS
        ):
            if re.match(
                r'^@!?\S+\s+' + re.escape(opcode) + r'(?:\s|;|$)',
                line.command,
            ):
                raise ValueError(
                    'predicated V0.4 %s consumer is unsupported' %
                    display_name
                )

    shader_type = ptx_shader.getShaderType()
    supported_shader_types = (
        ShaderType.Closest_hit,
        ShaderType.Any_hit,
        ShaderType.Intersection,
    )
    builtin_specs = {
        functional_type: (display_name, field_name)
        for functional_type, _, display_name, field_name in
        RTCORE_V04_SUPPORTED_DIRECT_HIT_BUILTINS
    }

    for index, line in enumerate(ptx_shader.lines):
        if line.instructionClass != InstructionClass.Functional:
            continue
        builtin_spec = builtin_specs.get(line.functionalType)
        if builtin_spec is None:
            continue
        display_name, field_name = builtin_spec
        if shader_type not in supported_shader_types:
            raise ValueError(
                'V0.4 %s consumer is invalid for shader %s' %
                (display_name, shader_type)
            )
        if len(line.args) != 1:
            raise ValueError(
                'V0.4 %s consumer requires one destination' % display_name
            )
        if line.condition:
            raise ValueError(
                'predicated V0.4 %s consumer is unsupported' % display_name
            )
        field_offset = rtcore_v04_direct_field_byte_offset(field_name)
        load = PTXFunctionalLine()
        load.leadingWhiteSpace = line.leadingWhiteSpace
        load.comment = line.comment
        load.buildString(
            'ld.global.u32',
            (
                line.args[0],
                rtcore_v04_handoff_word_address(
                    '%rt_handoff_lane_ptr', field_offset
                ),
            ),
        )
        ptx_shader.lines[index] = load


def translate_image_deref(ptx_shader):
    for index in range(len(ptx_shader.lines)):
        line = ptx_shader.lines[index]

        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.functionalType == FunctionalType.image_deref_store:
            # Ignore additional arguments (for now)
            image, arg2, arg3, hitValue, arg5, arg6, arg7 = line.args[0:7]
            args = line.args
            args[3:4] = [(hitValue + '_' + str(i)) for i in range(4)]
            args[1:2] = [(arg2 + '_' + str(i)) for i in range(4)]
            line.buildString(line.functionalType, args)
        
        elif line.functionalType == FunctionalType.image_deref_load:
            # Ignore additional arguments (for now)
            dst, image, location, arg3, arg4, arg5, arg6 = line.args[0:7]
            args = [image, dst, location, arg3, arg4, arg5, arg6]
            dstRegNames, _, _, _ = unwrapp_vector(ptx_shader, dst, dst)
            locationRegNames, _, _, _ = unwrapp_vector(ptx_shader, location, location)
            args[2:3] = locationRegNames
            args[1:2] = dstRegNames
            line.args[0:7] = args
            line.buildString(line.functionalType, line.args)


def translate_exit(ptx_shader):
    for index in range(len(ptx_shader.lines)):
        line = ptx_shader.lines[index]

        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.functionalType != FunctionalType.exit:
            continue

        line.buildString(FunctionalType.ret, ())


def translate_rt_shader_return_epilogue(ptx_shader):
    v04_shadow_return_publication = (
        rtcore_v04_shadow_shader_return_publication_enabled()
    )
    v04_builtin_consumer = rtcore_v04_shader_builtin_consumer_enabled()
    if not rtcore_symbolic_submit_enabled():
        return
    shader_type = ptx_shader.getShaderType()
    returns_to_rtcore = shader_type in (
        ShaderType.Any_hit,
        ShaderType.Intersection,
    )
    is_continuation_shader = shader_type in (
        ShaderType.Miss,
        ShaderType.Closest_hit,
        ShaderType.Any_hit,
        ShaderType.Intersection,
    )
    if not returns_to_rtcore and not (
        v04_builtin_consumer and is_continuation_shader
    ):
        return

    if v04_shadow_return_publication and returns_to_rtcore:
        commit_effect_spec = rtcore_v04_field_spec(
            'commit_retained_candidate'
        )
        accepted_report_effect_spec = rtcore_v04_field_spec(
            'accepted_reported_hit_valid'
        )
        terminate_effect_spec = rtcore_v04_field_spec('terminate_search')
        effect_word = commit_effect_spec[0]
        if any(spec[0] != effect_word for spec in (
            accepted_report_effect_spec, terminate_effect_spec
        )):
            raise ValueError('V0.4 traversal effects do not share one word')
        if any(spec[2] != 1 for spec in (
            commit_effect_spec,
            accepted_report_effect_spec,
            terminate_effect_spec,
        )):
            raise ValueError('V0.4 traversal effects are not single-bit fields')
        commit_effect_value = commit_effect_spec[3]
        accepted_report_effect_value = accepted_report_effect_spec[3]
        return_effect_offset = effect_word * 4
        if shader_type == ShaderType.Intersection:
            reported_t_offset = rtcore_v04_direct_field_byte_offset(
                'reported_t_fp32'
            )
            reported_hit_kind_spec = rtcore_v04_field_spec(
                'reported_hit_kind'
            )
            reported_metadata_word = reported_hit_kind_spec[0]
            if (reported_hit_kind_spec[1], reported_hit_kind_spec[2]) != (0, 8):
                raise ValueError(
                    'V0.4 reported hit kind is not the low byte of its word'
                )
            if any(
                rtcore_v04_field_spec(field_name)[0] != reported_metadata_word
                for field_name in (
                    'reported_attribute_word_count',
                    'reported_attribute_format',
                )
            ):
                raise ValueError(
                    'V0.4 reported metadata does not share one word'
                )
            reported_metadata_offset = reported_metadata_word * 4

    leading = '  '
    prologue = [
        PTXLine.createNewLine(leading + '.reg .b64 %rt_handoff_lane_ptr;\n'),
    ]
    if v04_builtin_consumer:
        prologue.extend([
            PTXLine.createNewLine(
                leading + '.reg .u32 %rt_v04_builtin_consumer_marker;\n'
            ),
            PTXLine.createNewLine(
                leading + '// rtcore_v04_shader_builtin_consumer ' +
                'profile=' + rtcore_abi_v04.PROFILE_ID + ' source_sha256=' +
                rtcore_abi_v04.SOURCE_INPUT_SHA256 + '\n'
            ),
        ])
    if returns_to_rtcore:
        prologue.extend([
            PTXLine.createNewLine(leading + '.reg .u32 %rt_hit_result;\n'),
            PTXLine.createNewLine(leading + '.reg .b32 %rt_reported_t;\n'),
            PTXLine.createNewLine(
                leading + '.reg .u32 %rt_reported_metadata;\n'
            ),
        ])
    if v04_shadow_return_publication and returns_to_rtcore:
        prologue.append(
            PTXLine.createNewLine(
                leading + '.reg .u32 %rt_v04_return_effect;\n'
            )
        )
        if shader_type == ShaderType.Intersection:
            prologue.extend([
                PTXLine.createNewLine(
                    leading + '.reg .u32 %rt_v04_reported_metadata;\n'
                ),
                PTXLine.createNewLine(
                    leading + '.reg .pred %rt_v04_has_report;\n'
                ),
            ])
        prologue.extend([
            PTXLine.createNewLine(
                leading + '// rtcore_v04_shadow_shader_return_publication ' +
                'profile=' + rtcore_abi_v04.PROFILE_ID + ' source_sha256=' +
                rtcore_abi_v04.SOURCE_INPUT_SHA256 + '\n'
            ),
            PTXLine.createNewLine(
                leading + 'mov.u32 %%rt_v04_return_effect, %u;\n' %
                (commit_effect_value
                 if shader_type == ShaderType.Any_hit else 0)
            ),
        ])
        if shader_type == ShaderType.Intersection:
            prologue.append(PTXLine.createNewLine(
                leading + 'mov.u32 %rt_v04_reported_metadata, 0;\n'
            ))

    for index, line in enumerate(ptx_shader.lines):
        if (line.instructionClass == InstructionClass.EntryPoint and
                'main' in line.fullLine):
            insertion_index = index + 1
            if '{' not in line.fullLine:
                while (insertion_index < len(ptx_shader.lines) and
                       ptx_shader.lines[insertion_index].fullLine.strip() != '{'):
                    insertion_index += 1
                insertion_index += 1
            ptx_shader.lines[insertion_index:insertion_index] = prologue
            break

    if not returns_to_rtcore:
        return

    index = 0
    while index < len(ptx_shader.lines):
        line = ptx_shader.lines[index]
        functional_type = getattr(line, 'functionalType', None)
        if functional_type == FunctionalType.ignore_ray_intersection:
            inserted = [
                PTXLine.createNewLine(line.leadingWhiteSpace +
                                      'mov.u32 %rt_hit_result, 3;\n')
            ]
            if v04_shadow_return_publication:
                inserted.append(PTXLine.createNewLine(
                    line.leadingWhiteSpace +
                    'mov.u32 %rt_v04_return_effect, 0;\n'
                ))
            ptx_shader.lines[index + 1:index + 1] = inserted
            index += len(inserted)
        elif functional_type == FunctionalType.report_ray_intersection:
            reported_predicate, reported_t, reported_hit_kind = line.args[:3]
            hit_result_move = PTXFunctionalLine()
            hit_result_move.leadingWhiteSpace = line.leadingWhiteSpace
            hit_result_move.condition = '@' + reported_predicate
            hit_result_move.buildString(
                'mov.u32', ('%rt_hit_result', '4'))
            reported_t_move = PTXFunctionalLine()
            reported_t_move.leadingWhiteSpace = line.leadingWhiteSpace
            reported_t_move.condition = '@' + reported_predicate
            reported_t_move.buildString(
                'mov.b32', ('%rt_reported_t', reported_t))
            metadata_move = PTXFunctionalLine()
            metadata_move.leadingWhiteSpace = line.leadingWhiteSpace
            metadata_move.condition = '@' + reported_predicate
            metadata_move.buildString(
                'mov.u32', ('%rt_reported_metadata', reported_hit_kind))
            inserted = [
                hit_result_move,
                reported_t_move,
                metadata_move,
            ]
            if v04_shadow_return_publication:
                v04_effect_move = PTXFunctionalLine()
                v04_effect_move.leadingWhiteSpace = line.leadingWhiteSpace
                v04_effect_move.condition = '@' + reported_predicate
                v04_effect_move.buildString(
                    'mov.u32', (
                        '%rt_v04_return_effect',
                        str(accepted_report_effect_value),
                    ))
                v04_metadata_move = PTXFunctionalLine()
                v04_metadata_move.leadingWhiteSpace = line.leadingWhiteSpace
                v04_metadata_move.condition = '@' + reported_predicate
                v04_metadata_move.buildString(
                    'mov.u32',
                    ('%rt_v04_reported_metadata', reported_hit_kind),
                )
                inserted.extend([v04_effect_move, v04_metadata_move])
            ptx_shader.lines[index + 1:index + 1] = inserted
            index += len(inserted)
        elif functional_type == FunctionalType.exit:
            epilogue = [
                PTXLine.createNewLine(line.leadingWhiteSpace +
                                      'st.global.u32 [%rt_handoff_lane_ptr + 56], '
                                      '%rt_reported_t;\n'),
                PTXLine.createNewLine(line.leadingWhiteSpace +
                                      'st.global.u32 [%rt_handoff_lane_ptr + 60], '
                                      '%rt_reported_metadata;\n'),
                PTXLine.createNewLine(line.leadingWhiteSpace +
                                      'st.global.u32 [%rt_handoff_lane_ptr + 52], '
                                      '%rt_hit_result;\n'),
            ]
            if v04_shadow_return_publication:
                if shader_type == ShaderType.Intersection:
                    has_report_test = PTXFunctionalLine()
                    has_report_test.leadingWhiteSpace = line.leadingWhiteSpace
                    has_report_test.buildString(
                        'setp.ne.u32',
                        ('%rt_v04_has_report',
                         '%rt_v04_return_effect', '0'),
                    )
                    reported_t_store = PTXFunctionalLine()
                    reported_t_store.leadingWhiteSpace = line.leadingWhiteSpace
                    reported_t_store.condition = '@%rt_v04_has_report'
                    reported_t_store.buildString(
                        'st.global.b32',
                        (rtcore_v04_handoff_word_address(
                            '%rt_handoff_lane_ptr', reported_t_offset
                         ), '%rt_reported_t'),
                    )
                    reported_metadata_store = PTXFunctionalLine()
                    reported_metadata_store.leadingWhiteSpace = (
                        line.leadingWhiteSpace
                    )
                    reported_metadata_store.condition = '@%rt_v04_has_report'
                    reported_metadata_store.buildString(
                        'st.global.u32',
                        (rtcore_v04_handoff_word_address(
                            '%rt_handoff_lane_ptr', reported_metadata_offset
                         ), '%rt_v04_reported_metadata'),
                    )
                    epilogue.extend([
                        has_report_test,
                        reported_t_store,
                        reported_metadata_store,
                    ])
                epilogue.extend([
                    PTXLine.createNewLine(
                        line.leadingWhiteSpace +
                        'st.global.u32 %s, %%rt_v04_return_effect;\n' %
                        rtcore_v04_handoff_word_address(
                            '%rt_handoff_lane_ptr', return_effect_offset
                        )
                    ),
                    PTXLine.createNewLine(
                        line.leadingWhiteSpace + 'membar.gl;\n'
                    ),
                ])
            ptx_shader.lines[index:index] = epilogue
            index += len(epilogue)
        index += 1


def translate_phi(ptx_shader):
    nextIndex = 0
    while nextIndex < len(ptx_shader.lines):
        index = nextIndex
        nextIndex += 1
    # for index in range(len(ptx_shader.lines)):
        line = ptx_shader.lines[index]
        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.functionalType != FunctionalType.phi:
            continue

        debug_print(line.fullLine)

        if len(line.args) == 5:
            dst, blockName0, src0, blockName1, src1 = line.args
        elif len(line.args) == 7:
            dst, blockName0, src0, blockName1, src1, blockName2, src2 = line.args
        
        dstDecleration, dstIndex = ptx_shader.findDeclaration(dst)
        debug_print(src0)
        debug_print(src1)
        src0Decleration, _ = ptx_shader.findDeclaration(src0)
        src1Decleration, _ = ptx_shader.findDeclaration(src1)

        if len(line.args) == 7:
            src2Decleration, _ = ptx_shader.findDeclaration(src2)

        if src0Decleration.variableType == src1Decleration.variableType:
            variableType = src0Decleration.variableType
        else: # this happens because of load_const types are unknown
            if src0Decleration.variableType[0:2] == '.f':
                variableType = src1Decleration.variableType
            elif src1Decleration.variableType[0:2] == '.f':
                variableType = src0Decleration.variableType
            elif src0Decleration.variableType[0:2] == '.u' and src1Decleration.variableType[0:2] == '.s':
                variableType = src1Decleration.variableType #lets go with .s for now
            elif src0Decleration.variableType[0:2] == '.s' and src1Decleration.variableType[0:2] == '.u':
                variableType = src0Decleration.variableType #lets go with .s for now
            else:
                assert 0

        dstDecleration.buildString(dstDecleration.declarationType, dstDecleration.vector, variableType, dstDecleration.variableName)

        src0Mov = PTXFunctionalLine()
        src0Mov.leadingWhiteSpace = src0Decleration.leadingWhiteSpace
        src0Mov.comment = line.comment
        src0Mov.buildString('mov%s' % variableType, (dst, src0))

        src1Mov = PTXFunctionalLine()
        src1Mov.leadingWhiteSpace = src1Decleration.leadingWhiteSpace
        src1Mov.comment = line.comment
        src1Mov.buildString('mov%s' % variableType, (dst, src1))

        if len(line.args) == 7:
            src2Mov = PTXFunctionalLine()
            src2Mov.leadingWhiteSpace = src2Decleration.leadingWhiteSpace
            src2Mov.comment = line.comment
            src2Mov.buildString('mov%s' % variableType, (dst, src2))


        ptx_shader.lines.remove(dstDecleration)
        ptx_shader.lines.remove(line)

        ptx_shader.addToStart((dstDecleration, PTXLine('\n')))
        ptx_shader.addToEndOfBlock((src0Mov, ), blockName0)
        ptx_shader.addToEndOfBlock((src1Mov, ), blockName1)

        if len(line.args) == 7:
            ptx_shader.addToEndOfBlock((src2Mov, ), blockName2)


def translate_load_const(ptx_shader):
    index = -1
    while index + 1 < len(ptx_shader.lines):
        index += 1
        line = ptx_shader.lines[index]
        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.functionalType != FunctionalType.load_const:
            continue

        dst, const = line.args
        declaration, _ = ptx_shader.findDeclaration(dst)
        declaration.isLoadConst = True

        line.buildString("mov%s" % (declaration.variableType), (dst, const))
        line.fullFunction = "mov%s" % (declaration.variableType)


        newVariableType = '.b' + declaration.variableType[2:]

        newDeclaration = PTXDecleration()
        newDeclaration.leadingWhiteSpace = declaration.leadingWhiteSpace
        newDeclaration.buildString(DeclarationType.Register, None, newVariableType, dst.replace('.', '_') + '_bits')

        newMov = PTXFunctionalLine()
        newMov.leadingWhiteSpace = line.leadingWhiteSpace
        newMov.buildString("mov%s" % (newDeclaration.variableType), (dst.replace('.', '_') + '_bits', const))

        ptx_shader.lines[index + 1:index + 1] = (newDeclaration, newMov)


def translate_const_operands(ptx_shader):
    def is_load_const_register(register_name):
        declaration, _ = ptx_shader.findDeclaration(register_name)
        return declaration is not None and declaration.isLoadConst

    for index in range(len(ptx_shader.lines)):
        line = ptx_shader.lines[index]
        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.command[:3] == 'mov':

            movType = line.command[3:]

            dst, src = line.args

            debug_print(line.fullLine)
            
            if src[0] == '%' and movType[:2] != '.f' and is_load_const_register(src):
                line.buildString(line.command.split()[0], (dst, src + '_bits'))
        
        elif line.command[:4] == 'setp':
            dst, src1, src2 = line.args

            type = '.' + line.command.split()[0].split('.')[2]

            if type[:2] != '.f':
                if src1[0] == '%' and is_load_const_register(src1):
                    line.buildString(line.command.split()[0], (dst, src1 + '_bits', src2))
            
                if src2[0] == '%' and is_load_const_register(src2):
                    line.buildString(line.command.split()[0], (dst, src1, src2 + '_bits'))
        
        elif line.command[:3] == 'add':
            dst, src1, src2 = line.args

            type = line.command[3:]

            if type[:2] != '.f':
                if src1[0] == '%' and is_load_const_register(src1):
                    line.buildString(line.command.split()[0], (dst, src1 + '_bits', src2))
            
                if src2[0] == '%' and is_load_const_register(src2):
                    line.buildString(line.command.split()[0], (dst, src1, src2 + '_bits'))
        

        elif line.command[:3] == 'mul':
            dst, src1, src2 = line.args

            type = line.command[3:]

            if type[:2] != '.f':
                if src1[0] == '%' and is_load_const_register(src1):
                    line.buildString(line.command.split()[0], (dst, src1 + '_bits', src2))
            
                if src2[0] == '%' and is_load_const_register(src2):
                    line.buildString(line.command.split()[0], (dst, src1, src2 + '_bits'))


        elif line.command[:3] == 'shl' or line.command[:3] == 'shr':
            dst, src1, src2 = line.args

            type = line.command[3:]
            if type[:2] != '.f':
                if src1[0] == '%' and is_load_const_register(src1):
                    line.buildString(line.command.split()[0], (dst, src1 + '_bits', src2))
            
                if src2[0] == '%' and is_load_const_register(src2):
                    line.buildString(line.command.split()[0], (dst, src1, src2 + '_bits'))
        
        elif line.command[:4] == 'selp':
            type = line.command[3:]
            if type[:2] != '.f':

                dst, src0, src1, src2 = line.args
                if src0[0] == '%' and is_load_const_register(src0):
                    line.buildString(line.command.split()[0], (dst, src0 + '_bits', src1, src2))

                dst, src0, src1, src2 = line.args
                if src1[0] == '%' and is_load_const_register(src1):
                    line.buildString(line.command.split()[0], (dst, src0, src1 + '_bits', src2))

        



        
def translate_f1_to_pred(ptx_shader):
    index = -1
    while index + 1 < len(ptx_shader.lines):
        index += 1
        line = ptx_shader.lines[index]
        # if line.instructionClass == InstructionClass.VariableDeclaration:

        #     if line.declarationType == DeclarationType.Register:

        #         if line.variableType == '.f1':
        #             line.buildString(DeclarationType.Register, line.vector, '.pred', line.variableName)
        

        if line.instructionClass == InstructionClass.Functional:

            if line.command.split()[0] == 'ld.global.b1':
                
                dst, ptr = line.args
                declaration, _ = ptx_shader.findDeclaration(dst)

                assert declaration.variableType == '.b1'

                newDeclaration = PTXDecleration()
                newDeclaration.leadingWhiteSpace = line.leadingWhiteSpace
                newDeclaration.buildString(DeclarationType.Register, None, '.u16', declaration.variableName + '_u16')

                newLoad = PTXFunctionalLine()
                newLoad.leadingWhiteSpace = line.leadingWhiteSpace
                newLoad.buildString('ld.global.u16', (dst + '_u16', ptr))

                newAnd = PTXFunctionalLine()
                newAnd.leadingWhiteSpace = line.leadingWhiteSpace
                newAnd.buildString('and.b16', (dst + '_u16', dst + '_u16', '%const1_u16'))

                newSetp = PTXFunctionalLine()
                newSetp.leadingWhiteSpace = line.leadingWhiteSpace
                newSetp.buildString('setp.eq.u16', (dst, dst + '_u16', '%const1_u16'))


                declaration.buildString(declaration.declarationType, declaration.vector, '.pred', declaration.variableName)
                ptx_shader.lines.remove(line)
                ptx_shader.lines[index:index] = (newDeclaration, newLoad, newAnd, newSetp)
            

def add_consts(ptx_shader):
    const1_u16_declaration = PTXDecleration()
    const1_u16_declaration.leadingWhiteSpace = '\t'
    const1_u16_declaration.buildString(DeclarationType.Register, None, '.u16', '%const1_u16')

    const1_u16_mov = PTXFunctionalLine()
    const1_u16_mov.leadingWhiteSpace = '\t'
    const1_u16_mov.buildString('mov.u16', ('%const1_u16', '1'))

    ptx_shader.addToStart((const1_u16_declaration, const1_u16_mov, PTXLine('\n')))



    const0_u32_declaration = PTXDecleration()
    const0_u32_declaration.leadingWhiteSpace = '\t'
    const0_u32_declaration.buildString(DeclarationType.Register, None, '.u32', '%const0_u32')

    const0_u32_Mov = PTXFunctionalLine()
    const0_u32_Mov.leadingWhiteSpace = '\t'
    const0_u32_Mov.buildString('mov.u32', ('%const0_u32', '0'))

    ptx_shader.addToStart((const0_u32_declaration, const0_u32_Mov, PTXLine('\n')))



    const0_f32_declaration = PTXDecleration()
    const0_f32_declaration.leadingWhiteSpace = '\t'
    const0_f32_declaration.buildString(DeclarationType.Register, None, '.f32', '%const0_f32')

    const0_f32_mov = PTXFunctionalLine()
    const0_f32_mov.leadingWhiteSpace = '\t'
    const0_f32_mov.buildString('mov.f32', ('%const0_f32', '0F00000000'))

    ptx_shader.addToStart((const0_f32_declaration, const0_f32_mov, PTXLine('\n')))


    const1_f32_declaration = PTXDecleration()
    const1_f32_declaration.leadingWhiteSpace = '\t'
    const1_f32_declaration.buildString(DeclarationType.Register, None, '.f32', '%const1_f32')

    const1_f32_mov = PTXFunctionalLine()
    const1_f32_mov.leadingWhiteSpace = '\t'
    const1_f32_mov.buildString('mov.f32', ('%const1_f32', '0F3f800000'))

    ptx_shader.addToStart((const1_f32_declaration, const1_f32_mov, PTXLine('\n')))


def add_temps(ptx_shader):
    temp_pred_declaration = PTXDecleration()
    temp_pred_declaration.leadingWhiteSpace = '\t'
    temp_pred_declaration.buildString(DeclarationType.Register, None, '.pred', '%temp_pred')

    ptx_shader.addToStart((temp_pred_declaration, ))


    temp_f32_declaration = PTXDecleration()
    temp_f32_declaration.leadingWhiteSpace = '\t'
    temp_f32_declaration.buildString(DeclarationType.Register, None, '.f32', '%temp_f32')

    ptx_shader.addToStart((temp_f32_declaration, ))


    temp_u32_declaration = PTXDecleration()
    temp_u32_declaration.leadingWhiteSpace = '\t'
    temp_u32_declaration.buildString(DeclarationType.Register, None, '.u32', '%temp_u32')

    ptx_shader.addToStart((temp_u32_declaration, ))


    temp_u64_declaration = PTXDecleration()
    temp_u64_declaration.leadingWhiteSpace = '\t'
    temp_u64_declaration.buildString(DeclarationType.Register, None, '.u64', '%temp_u64')

    ptx_shader.addToStart((temp_u64_declaration, ))


    ptx_shader.addToStart((PTXLine('\n'), ))



def translate_ALU(ptx_shader):
    index = -1
    while index + 1 < len(ptx_shader.lines):
        index += 1
        line = ptx_shader.lines[index]
        
        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.functionalType == FunctionalType.fpow:
            dst, src1, src2 = line.args # dst = src1 ^ src2 ?

            declaration, _ = ptx_shader.findDeclaration(dst)
            assert declaration.variableType == '.f32'

            logLine = PTXFunctionalLine()
            logLine.leadingWhiteSpace = line.leadingWhiteSpace
            logLine.buildString('lg2.approx.f32', (dst, src1))

            mulLine = PTXFunctionalLine()
            mulLine.leadingWhiteSpace = line.leadingWhiteSpace
            mulLine.buildString('mul.f32', (dst, dst, src2))

            expLine = PTXFunctionalLine()
            expLine.leadingWhiteSpace = line.leadingWhiteSpace
            expLine.buildString('ex2.approx.f32', (dst, dst))

            ptx_shader.lines.remove(line)
            ptx_shader.lines[index:index] = (logLine, mulLine, expLine)
        

        elif line.functionalType == FunctionalType.flrp:
            dst, src0, src1, src2 = line.args # dst = src0 * (1 - src2) + src1 * src2

            sub = PTXFunctionalLine()
            sub.leadingWhiteSpace = line.leadingWhiteSpace
            sub.buildString('sub.f32', (dst, '%const1_f32', src2))

            mul0 = PTXFunctionalLine()
            mul0.leadingWhiteSpace = line.leadingWhiteSpace
            mul0.buildString('mul.f32', (dst, src0, dst))

            mul1 = PTXFunctionalLine()
            mul1.leadingWhiteSpace = line.leadingWhiteSpace
            mul1.buildString('mul.f32', ('%temp_f32', src2, src1))

            add = PTXFunctionalLine()
            add.leadingWhiteSpace = line.leadingWhiteSpace
            add.comment = line.comment
            add.buildString('add.f32', (dst, dst, '%temp_f32'))

            ptx_shader.lines[index:index + 1] = (sub, mul0, mul1, add)
        

        elif line.functionalType == FunctionalType.bcsel:
            dst, src0, src1, src2 = line.args

            src1Declaration, _ = ptx_shader.findDeclaration(src1)
            src2Declaration, _ = ptx_shader.findDeclaration(src2)
            if not src1Declaration.isLoadConst:
                type = src1Declaration.variableType
            elif not src2Declaration.isLoadConst:
                type = src2Declaration.variableType
            else:
                type = '.f32'
            
            dstDeclaration, _ = ptx_shader.findDeclaration(dst)
            dstDeclaration.buildString(dstDeclaration.declarationType, dstDeclaration.vector, type, dstDeclaration.variableName)

            line.buildString('selp' + type, (dst, src1, src2, src0))

            # line.buildString('selp.f32', (dst, src1, src2, src0))
        
        elif line.functionalType == FunctionalType.pack_64_2x32_split:
            dst, src0, src1 = line.args

            src0Declaration, _ = ptx_shader.findDeclaration(src0)
            assert src0Declaration.variableType == '.u32'

            cvt1 = PTXFunctionalLine()
            cvt1.leadingWhiteSpace = line.leadingWhiteSpace
            cvt1.buildString('cvt.u64.u32', ('%temp_u64', src1))

            shl = PTXFunctionalLine()
            shl.leadingWhiteSpace = line.leadingWhiteSpace
            shl.buildString('shl.b64', (dst, '%temp_u64', src1))

            cvt0 = PTXFunctionalLine()
            cvt0.leadingWhiteSpace = line.leadingWhiteSpace
            cvt0.buildString('cvt.u64.u32', ('%temp_u64', src0))

            orLine = PTXFunctionalLine()
            orLine.leadingWhiteSpace = line.leadingWhiteSpace
            orLine.comment = line.comment
            orLine.buildString('or.b64', (dst, dst, '%temp_u64'))

            ptx_shader.lines[index:index + 1] = (cvt1, shl, cvt0, orLine)
        
        elif line.functionalType == FunctionalType.b2f32:
            dst, src = line.args
            line.buildString('selp.f32', (dst, '0F3f800000', '0F00000000', src))
        
        elif line.functionalType == FunctionalType.fsign:
            dst, src = line.args

            ldLine = PTXFunctionalLine()
            ldLine.leadingWhiteSpace = line.leadingWhiteSpace
            ldLine.buildString('mov.f32', (dst, '0F3f800000'))

            copysignfLine = PTXFunctionalLine()
            copysignfLine.leadingWhiteSpace = line.leadingWhiteSpace
            copysignfLine.comment = line.comment
            copysignfLine.buildString('copysignf', (dst, src))

            ptx_shader.lines[index:index + 1] = (ldLine, copysignfLine)
        

        elif line.functionalType == FunctionalType.fsat:
            dst, src = line.args

            maxLine = PTXFunctionalLine()
            maxLine.leadingWhiteSpace = line.leadingWhiteSpace
            maxLine.buildString('max.f32', (dst, src, '%const0_f32'))

            minLine = PTXFunctionalLine()
            minLine.leadingWhiteSpace = line.leadingWhiteSpace
            minLine.buildString('min.f32', (dst, dst, '%const1_f32'))

            ptx_shader.lines[index:index + 1] = (maxLine, minLine)





def translate_texture_instructions(ptx_shader):
    for index in range(len(ptx_shader.lines)):
        line = ptx_shader.lines[index]
        
        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.functionalType == FunctionalType.txl:
            dst, texture, sampler, coord, lod = line.args

            newDstNames, _, _, _ = unwrapp_vector(ptx_shader, dst, dst)
            newCoordNames, _, _, _ = unwrapp_vector(ptx_shader, coord, coord)
            line.buildString(line.functionalType, [texture, sampler] + newDstNames + newCoordNames[0:2] + [lod, ])
            


def translate_special_intrinsics(ptx_shader):
    for index in range(len(ptx_shader.lines)):
        line = ptx_shader.lines[index]
        
        if line.instructionClass != InstructionClass.Functional:
            continue

        if line.functionalType == FunctionalType.shader_clock:
            dst, memory_scope = line.args
            newRegNames, _, _, _ = unwrapp_vector(ptx_shader, dst, dst)
            line.buildString(FunctionalType.shader_clock, newRegNames[0:2])
        
        # if line.functionalType == FunctionalType.report_ray_intersection:
        #     dst, src0, src1 = line.args

        #     # dstDeclaration, dstDeclarationIndex = ptx_shader.findDeclaration(dst)
        #     line.buildString(line.functionalType, ('%temp_u32', src0, src1))

        #     setpLine = PTXFunctionalLine()
        #     setpLine.leadingWhiteSpace = line.leadingWhiteSpace
        #     setpLine.buildString('setp.ne.u32', (dst, '%temp_u32', '%const0_u32'))

        #     ptx_shader.lines[index + 1:index + 1] = (setpLine, )



def add_extra_thread_return(ptx_shader):
    thread_return_code = """.reg .u32 %launch_ID_0;
.reg .u32 %launch_ID_1;
.reg .u32 %launch_ID_2;
load_ray_launch_id %launch_ID_0, %launch_ID_1, %launch_ID_2;

.reg .u32 %launch_Size_0;
.reg .u32 %launch_Size_1;
.reg .u32 %launch_Size_2;
load_ray_launch_size %launch_Size_0, %launch_Size_1, %launch_Size_2;


.reg .pred %bigger_0;
setp.ge.u32 %bigger_0, %launch_ID_0, %launch_Size_0;

.reg .pred %bigger_1;
setp.ge.u32 %bigger_1, %launch_ID_1, %launch_Size_1;

.reg .pred %bigger_2;
setp.ge.u32 %bigger_2, %launch_ID_2, %launch_Size_2;

@%bigger_0 bra shader_exit;
@%bigger_1 bra shader_exit;
@%bigger_2 bra shader_exit;"""

    lines = [PTXLine('\t' + line + '\n') for line in thread_return_code.split("\n")]
    lines.append(PTXLine('\n'))

    ptx_shader.addToStart(lines)








def main():
    unique_ID = 0
    assert len(sys.argv) == 2
    shaderFolder = sys.argv[1]

    shaders = []
    for shaderFile in os.listdir(shaderFolder):
        shaders.append(PTXShader(os.path.join(shaderFolder, shaderFile)))
    
    shaderIDs = {}
    for shader in shaders:
        if shader.getShaderType() in shaderIDs:
            shaderIDs[shader.getShaderType()].append(shader.getShaderID())
        else:
            shaderIDs[shader.getShaderType()] = [shader.getShaderID(), ]

    
    for shader in shaders:
        print("Translating {}".format(shader.filePath))
        rtcore_prepare_continuation_ptx_profile(shader)
        add_consts(shader)
        add_temps(shader)

        translate_load_const(shader)
        translate_descriptor_set_instructions(shader)
        translate_deref_instructions(shader)
        translate_trace_ray(shader, shaderIDs)
        translate_decl_var(shader)
        translate_rt_shader_builtin_consumers(shader)
        translate_load_GL_instructions(shader)
        translate_image_deref(shader)
        translate_rt_shader_return_epilogue(shader)
        translate_exit(shader)
        translate_texture_instructions(shader)
        translate_special_intrinsics(shader)

        translate_vector_operands(shader, unique_ID)

        translate_ALU(shader)

        translate_phi(shader)
        
        translate_const_operands(shader)

        translate_f1_to_pred(shader)

        if shader.getShaderType() == ShaderType.Ray_generation:
            add_extra_thread_return(shader)
        

        shader.writeToFile()


if __name__ == '__main__':
    main()
