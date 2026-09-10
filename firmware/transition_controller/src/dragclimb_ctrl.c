/* dragclimb_ctrl.c —— 段 I：倒拖垂直爬升控制器
 *
 * 姿态：机头朝下（俯仰 -90°），4 桨对转、推力竖直向上。
 * 稳定：**被动摆式为主**；差动推力仅做阻尼（横向 CG < 3 mm 是前提，必须实测）。
 * 周期：500 Hz（与飞控同频）。
 *
 * ⚠ 参考实现：未编译、未 SITL、未实飞。
 * ⚠ 正式工程应把结构体与声明拆到 dragclimb_ctrl.h。
 *
 * 依据：[docs/09] 9.5 / [docs/07] 7.2.2 / [transition_controller/README.md](../README.md)
 */

#include <math.h>

#ifndef PI
#define PI 3.14159265358979323846f
#endif

/* ------------------------------------------------------------------ */
/* 结构体（自包含，正式工程拆 .h）                                      */
/* ------------------------------------------------------------------ */
typedef struct {
    float kp_climb;      /* 爬升率 P 增益               */
    float kd_rate;       /* 角速率阻尼增益              */
    float target_rate;   /* 目标爬升率 (m/s)            */
    float h_cutoff;      /* 关机高度 (m) = 150          */
    float hover_thr;     /* 悬停油门 ≈ 0.72             */
    float thr_min;       /* 关机前减速门限 (m/s)        */
    uint8_t shutdown;    /* 已关机标志 → 进段 II        */
} dragclimb_t;

/* ------------------------------------------------------------------ */
/* 初始化                                                              */
/* ------------------------------------------------------------------ */
void dragclimb_init(dragclimb_t* s)
{
    s->kp_climb     = 0.15f;
    s->kd_rate      = 0.08f;
    s->target_rate  = 3.33f;   /* 150 m / 45 s ≈ 3.33 m/s */
    s->h_cutoff     = 150.0f;  /* CLIMB_CUTOFF_H          */
    s->hover_thr    = 0.72f;   /* 悬停油门（实测定）      */
    s->thr_min      = 1.0f;    /* 爬升率 > 1 m/s 先减速   */
    s->shutdown     = 0u;
}

/* ------------------------------------------------------------------ */
/* 段 I 主循环（500 Hz）                                               */
/*                                                                     */
/*   h          : AGL 高度 (m)                                         */
/*   climb_rate : 爬升率 (m/s)，上为正                                  */
/*   w[3]       : 陀螺角速率 (rad/s) = [p, q, r]                       */
/*   out[4]     : 4 个电机油门指令 0.0 ~ 1.0                           */
/* ------------------------------------------------------------------ */
void dragclimb_update(dragclimb_t* s,
                      float h,
                      float climb_rate,
                      const float w[3],
                      float out[4])
{
    float thrust;

    /* 1) 总推力：低于关机高度时保持目标爬升率；到高即关机顺桨
     *    （若爬升速率 > 1 m/s，先减速再关机，减少上飘过冲）
     */
    if (h < s->h_cutoff) {
        if (climb_rate > s->thr_min && (s->h_cutoff - h) < 5.0f) {
            thrust = s->hover_thr * 0.6f;               /* 减速段 */
        } else {
            thrust = s->hover_thr + s->kp_climb * (s->target_rate - climb_rate);
        }
        if (thrust < 0.0f) thrust = 0.0f;
        if (thrust > 1.0f) thrust = 1.0f;
    } else {
        thrust = 0.0f;
        s->shutdown = 1u;      /* → 顺桨 → 段 II（deploy_ctrl） */
    }

    /* 2) 阻尼：4 电机差动，产生与机体角速率反向的力矩
     *    （倒拖时"横滚"即绕水平轴倾斜；摆式稳定 + 此阻尼即可，
     *      **不做全姿态闭环**）
     */
    const float d_p = s->kd_rate * w[0];
    const float d_q = s->kd_rate * w[1];

    /* 3) 分配（X 型，相邻反向） */
    const float ang[4] = { PI / 4.0f, 3.0f * PI / 4.0f, 5.0f * PI / 4.0f, 7.0f * PI / 4.0f };
    for (int i = 0; i < 4; i++) {
        out[i] = thrust * 0.25f + d_p * sinf(ang[i]) + d_q * cosf(ang[i]);
        if (out[i] < 0.0f) out[i] = 0.0f;
        if (out[i] > 1.0f) out[i] = 1.0f;
    }
}

/* ------------------------------------------------------------------ */
/* 已知简化（落地必须补，见 README 第 7 节）                            */
/*   · 没有全姿态闭环（设计如此，但依赖横向 CG < 3 mm）                 */
/*   · 增益为初值，必须 AutoTune / 系留实测标定                          */
/*   · 未建模阵风与谷风扰动                                             */
/* ------------------------------------------------------------------ */
