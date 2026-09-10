/* test_deploy_gate.c —— 段 II 撑开门控真值表单测
 *
 * 目的：把 [transition_controller/README.md](../README.md) 第 4 节的真值表固化成可跑的断言，
 *      尤其是「**硬件互锁断线必须禁止撑开**」这条安全性质。
 *
 * 运行（示例）：
 *   gcc -std=c99 -Wall -Wextra -I. test_deploy_gate.c -o test_gate -lm && ./test_gate
 *
 * 说明：`gate_open()` 在 deploy_ctrl.c 中是 static，本测试采用**直接包含源文件**的做法
 *      （小型 C 工程的常见手段），并先把外部依赖桩掉，避免链接器找硬件函数。
 *      正式工程建议改成分离编译 + 测试替身（mock）。
 */

#include <stdio.h>
#include <math.h>
#include <assert.h>

/* ---------- 1) 先桩掉 deploy_ctrl.c 用到的外部依赖 ---------- */
static int s_motors_off = 0, s_feather = 0, s_dive = 0, s_latch = 0;
static int s_pull = 0, s_ratchet = 0, s_restart = 0, s_handover = 0, s_abort = 0;

void motors_off(void)                    { s_motors_off++; }
void props_feather(void)                 { s_feather++; }
void dive_damping_only(void)             { s_dive++; }
void latch_release_pulse(void)           { s_latch++; }
void elevator_pull_g(float g)            { (void)g; s_pull++; }
void ratchet_to_cruise_cmd(void)         { s_ratchet++; }
void motors_restart(void)                { s_restart++; }
void handover_to_ardupilot(void)         { s_handover++; }
void emergency_nose_down_profile(void)   { s_abort++; }

/* ---------- 2) 包含被测源 ---------- */
#include "../src/deploy_ctrl.c"

/* ---------- 3) 真值表 ---------- */
typedef struct {
    float   airspeed;
    float   agl;
    uint8_t il_deploy_ok;
    uint8_t expect;      /* 期望 gate_open 结果 */
    const char* name;
} gate_case_t;

static const gate_case_t CASES[] = {
    /* 空速,   高度,  IL, 期望, 说明 */
    { 21.0f,  95.0f, 1, 1, "空速够 + 高度够 + 互锁OK → 开"          },
    { 20.9f,  90.0f, 1, 1, "边界值（>=）→ 开"                       },
    { 20.89f, 90.0f, 1, 0, "空速差 0.01 → 等"                       },
    { 21.0f,  89.9f, 1, 0, "高度差 0.1 → 等"                        },
    { 20.0f,  95.0f, 1, 0, "空速不足（< 1.1 Vs）→ 等"                },
    { 21.0f,  85.0f, 1, 0, "高度不足（< 90 m）→ 等"                  },
    { 21.0f,  95.0f, 0, 0, "**互锁断线 → 禁止撑开**（安全性质）"      },
    { 25.0f, 120.0f, 0, 0, "条件全优但互锁断线 → 仍禁止"             },
};

int main(void)
{
    dc_cfg_t c; deploy_ctrl_defaults(&c);
    int fail = 0;

    printf("=== deploy gate truth table ===\n");
    for (size_t i = 0; i < sizeof(CASES) / sizeof(CASES[0]); i++) {
        const gate_case_t* k = &CASES[i];
        dc_in_t in = {0};
        in.airspeed     = k->airspeed;
        in.agl          = k->agl;
        in.il_deploy_ok = k->il_deploy_ok;

        uint8_t got = gate_open(&in, &c);
        int ok = (got == k->expect);
        printf("[%s] v=%.2f h=%.1f IL=%u -> %u (expect %u)  %s\n",
               ok ? "PASS" : "FAIL", k->airspeed, k->agl,
               k->il_deploy_ok, got, k->expect, k->name);
        if (!ok) fail++;
    }

    /* 附加：拉平完成判据 */
    {
        dc_in_t in = {0};
        in.pitch_deg = 10.0f; in.airspeed = 22.0f;   /* |θ|<15 且 >1.15Vs=21.85 */
        assert(flare_done(&in, &c) == 1);
        in.airspeed = 21.0f;
        assert(flare_done(&in, &c) == 0);
        in.airspeed = 22.0f; in.pitch_deg = 20.0f;
        assert(flare_done(&in, &c) == 0);
        printf("[PASS] flare_done boundary checks\n");
    }

    /* 附加：高度用尽 → 备用剖面（走状态机） */
    {
        dc_ctx_t x = { DC_DIVE, 0u, 0u };
        dc_in_t in = {0};
        in.airspeed = 21.0f; in.agl = 40.0f;   /* < 90*0.5 = 45 */
        in.il_deploy_ok = 1; in.now_ms = 1000u;
        deploy_ctrl_update(&x, &c, &in);
        if (x.st != DC_ABORT_PROFILE) { printf("[FAIL] 高度用尽未进入备用剖面\n"); fail++; }
        else printf("[PASS] 高度用尽 → ABORT_PROFILE\n");
        if (s_abort != 1) { printf("[FAIL] 备用剖面未被调用\n"); fail++; }
    }

    printf("\n%s (%d failed)\n", fail ? "FAILED" : "ALL PASSED", fail);
    return fail ? 1 : 0;
}
