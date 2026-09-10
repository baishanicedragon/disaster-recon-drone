/* deploy_ctrl.c —— 段 II：关机 → 俯冲 → 撑开 → 2.0 g 拉平 → 切档 → 重启
 *
 * 时序状态机（挂在 ArduPilot AUTO 之外）：
 *   CUTOFF → DIVE → DEPLOY → FLARE → RATCHET → RESTART → DONE
 *                      ↘（门控失败 / 超时）→ ABORT_PROFILE（机头朝下迫降）
 *
 * ⚠ 参考实现：未编译、未 SITL、未实飞。
 * ⚠ **撑开与切档的解锁依据必须是硬件互锁信号，不是软件判据。**
 *
 * 依据：[docs/07] 7.2.2 / [docs/09] 9.5 / [docs/18] 18.8
 *      [hardware/interface/pinmap.md] IL_DEPLOY_OK / IL_WING_LOCK_* / IL_RATCHET_CRUISE
 */

#include <math.h>
#include <stdint.h>

/* ---------------- 状态 ---------------- */
typedef enum {
    DC_CUTOFF = 0,      /* 关机 + 顺桨                     */
    DC_DIVE,            /* 头朝下俯冲增速，只做阻尼         */
    DC_DEPLOY,          /* 门控满足 → 物理解锁棘爪，双翼撑开 */
    DC_FLARE,           /* 2.0 g 拉平（上限 2.5 g）         */
    DC_RATCHET,         /* 棘轮切巡航小距档（一次性锁存）    */
    DC_RESTART,         /* 重启电机 → 交还 ArduPilot        */
    DC_DONE,
    DC_ABORT_PROFILE    /* 机头朝下迫降备用剖面             */
} dc_state_t;

/* ---------------- 配置 ---------------- */
typedef struct {
    float vs_thresh;        /* 撑开门控空速 = 20.9 (1.1 Vs)   */
    float h_deploy_min;     /* 撑开门控最低高度 = 90 m        */
    float vs_dive_target;   /* 俯冲目标 = 1.25 Vs ≈ 23.4      */
    float vs_1g;            /* 失速速度 Vs = 19.0             */
    float g_cmd;            /* 指令过载 = 2.0                 */
    float g_max;            /* 上限 = 2.5，超限自动缓拉        */
    float flare_pitch_deg;  /* 拉平完成俯仰门限 = 15°         */
    uint16_t lock_timeout_ms;   /* 撑开/锁销确认超时            */
    uint16_t ratchet_timeout_ms;/* 棘轮换档超时                */
} dc_cfg_t;

/* ---------------- 输入 ---------------- */
typedef struct {
    float airspeed;         /* m/s                            */
    float agl;              /* m（气压 − DEM，见 docs/18 18.4）*/
    float pitch_deg;        /* 俯仰角                         */
    float g_meas;           /* 实测法向过载                   */
    uint8_t il_deploy_ok;   /* IL_DEPLOY_OK  断线=0            */
    uint8_t il_wing_lock_l; /* IL_WING_LOCK_L 断线=0           */
    uint8_t il_wing_lock_r; /* IL_WING_LOCK_R                 */
    uint8_t il_ratchet;     /* IL_RATCHET_CRUISE               */
    uint32_t now_ms;        /* 当前时刻                       */
} dc_in_t;

/* ---------------- 内部上下文 ---------------- */
typedef struct {
    dc_state_t st;
    uint32_t   t_enter_ms;
    uint8_t    latch_fired;
} dc_ctx_t;

/* ---------------- 门控 ----------------
 * 软件判据**只用于状态机进度与日志**；
 * `il_deploy_ok` 是硬线互锁（动压开关 ∧ 高度比较），断线 → 0 → 禁止撑开。
 */
static uint8_t gate_open(const dc_in_t* in, const dc_cfg_t* c)
{
    uint8_t sw = (in->airspeed >= c->vs_thresh) && (in->agl >= c->h_deploy_min);
    return (uint8_t)(sw && in->il_deploy_ok);
}

/* 拉平完成判据：|θ| < 15° 且 空速 > 1.15 Vs */
static uint8_t flare_done(const dc_in_t* in, const dc_cfg_t* c)
{
    return (fabsf(in->pitch_deg) < c->flare_pitch_deg)
        && (in->airspeed > 1.15f * c->vs_1g);
}

static void go(dc_ctx_t* x, dc_state_t s, uint32_t now)
{
    x->st = s; x->t_enter_ms = now;
}

/* ---------------- 主更新（建议 ≥ 200 Hz） ---------------- */
void deploy_ctrl_update(dc_ctx_t* x, const dc_cfg_t* c, const dc_in_t* in)
{
    const uint32_t dt = in->now_ms - x->t_enter_ms;

    switch (x->st) {

    case DC_CUTOFF:
        motors_off();               /* 4 电机停转 */
        props_feather();            /* 桨叶气动顺桨折叠 */
        go(x, DC_DIVE, in->now_ms);
        break;

    case DC_DIVE:
        /* 只做阻尼（角速率阻尼 + 小量配平），不急于改出 */
        dive_damping_only();
        if (gate_open(in, c)) {
            go(x, DC_DEPLOY, in->now_ms);
        } else if (in->agl < c->h_deploy_min * 0.5f) {
            /* 高度已用尽仍不满足 → 放弃改平 */
            go(x, DC_ABORT_PROFILE, in->now_ms);
        }
        break;

    case DC_DEPLOY:
        /* 弹簧驱动、无舵机：只需给一次解锁脉冲，物理解锁由 IL_DEPLOY_OK 完成 */
        if (!x->latch_fired) {
            latch_release_pulse();  /* 解锁棘爪 */
            x->latch_fired = 1u;
        }
        if (in->il_wing_lock_l && in->il_wing_lock_r) {
            go(x, DC_FLARE, in->now_ms);
        } else if (dt > c->lock_timeout_ms) {
            go(x, DC_ABORT_PROFILE, in->now_ms);   /* 未锁 → 不进拉平 */
        }
        break;

    case DC_FLARE:
        /* 2.0 g 拉起，俯冲 -90° → 水平；超过 2.5 g 自动缓拉 */
        {
            float g = c->g_cmd;
            if (in->g_meas > c->g_max) g = c->g_max;
            elevator_pull_g(g);
        }
        if (flare_done(in, c)) {
            go(x, DC_RATCHET, in->now_ms);
        } else if (dt > c->lock_timeout_ms) {
            go(x, DC_ABORT_PROFILE, in->now_ms);
        }
        break;

    case DC_RATCHET:
        /* 电磁销/棘轮：桨距 爬升大距 → 巡航小距（一次性，锁存） */
        ratchet_to_cruise_cmd();
        if (in->il_ratchet) {
            go(x, DC_RESTART, in->now_ms);
        } else if (dt > c->ratchet_timeout_ms) {
            /* 未锁巡航档 → 禁止电机重启（硬件也会拒绝） */
            go(x, DC_ABORT_PROFILE, in->now_ms);
        }
        break;

    case DC_RESTART:
        motors_restart();           /* 离心甩开折叠桨叶 */
        handover_to_ardupilot();    /* 交还 AUTO / 地形跟随 */
        go(x, DC_DONE, in->now_ms);
        break;

    case DC_ABORT_PROFILE:
        emergency_nose_down_profile();   /* 备用剖面，见 docs/07 7.2.2 */
        break;

    case DC_DONE:
    default:
        break;
    }
}

/* ---------------- 默认配置 ---------------- */
void deploy_ctrl_defaults(dc_cfg_t* c)
{
    c->vs_thresh       = 20.9f;   /* SCR_USER1 */
    c->h_deploy_min    = 90.0f;   /* SCR_USER2 */
    c->vs_dive_target  = 23.4f;   /* 1.25 Vs   */
    c->vs_1g           = 19.0f;
    c->g_cmd           = 2.0f;
    c->g_max           = 2.5f;
    c->flare_pitch_deg = 15.0f;
    c->lock_timeout_ms    = 1500u;
    c->ratchet_timeout_ms = 1200u;
}

/* ---------------- 外部依赖（由飞控/HAL 提供，本文件只声明） ----------------
 *   void motors_off(void);
 *   void props_feather(void);
 *   void dive_damping_only(void);
 *   void latch_release_pulse(void);
 *   void elevator_pull_g(float g);
 *   void ratchet_to_cruise_cmd(void);
 *   void motors_restart(void);
 *   void handover_to_ardupilot(void);
 *   void emergency_nose_down_profile(void);
 */
