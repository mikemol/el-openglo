#version 300 es
// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 Mike Mol
//
// el-segment.glsl - ONE fragment shader for every el-openglo display (W153).
//
// Draw each node of catalog/engines/el-seg{7,16,22}.glb / el-matrix-5x7.glb with
// u_index = that node's position in the file's node order (the same order as
// el-glyphs.json "segments"), and u_mask = the glyph's bitmask from el-glyphs.json
// (bit i = node i; uvec2 so the 35-dot matrix fits: x = bits 0-31, y = bits 32-63).
//
// Colours come from catalog/el-openglo.tokens.json, group <variant>.material:
//   u_base     = material.base       the ground (unlit substrate)
//   u_emissive = material.emissive   a lit segment
//   u_ghost    = material.ghost      an unlit segment's phosphor colour
//   u_ghost_a  = material.ghost_opacity  how much ghost shows over the ground
//
// THE RELATION (relations.md §3b): an unlit segment is ghost composited over
// base at ghost_opacity; a lit segment is emissive. Bloom is a blur of the LIT
// layer only, so o_bloom carries emissive for lit fragments and black for the
// rest: blur o_bloom in a separate pass and add it over o_color.
//
// (#version is line 1 because GLSL ES requires it before any comment.)
precision mediump float;

uniform uvec2 u_mask;
uniform uint  u_index;
uniform vec3  u_base;
uniform vec3  u_emissive;
uniform vec3  u_ghost;
uniform float u_ghost_a;

layout(location = 0) out vec4 o_color;
layout(location = 1) out vec4 o_bloom;

bool lit(uvec2 mask, uint i) {
    uint word = i < 32u ? mask.x : mask.y;
    return ((word >> (i & 31u)) & 1u) == 1u;
}

void main() {
    if (lit(u_mask, u_index)) {
        o_color = vec4(u_emissive, 1.0);
        o_bloom = vec4(u_emissive, 1.0);
    } else {
        o_color = vec4(mix(u_base, u_ghost, u_ghost_a), 1.0);
        o_bloom = vec4(0.0, 0.0, 0.0, 1.0);
    }
}
