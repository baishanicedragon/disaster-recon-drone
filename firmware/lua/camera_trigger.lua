--[[
  camera_trigger.lua · 等距相机触发

  依据 [docs/09] 9.2：盘旋段用**距离触发**而非时间触发，保证前后帧重叠率稳定。

    GSD              = h × p / f        （h = AGL, p = 1.55 µm, f = 6 mm）
    W_ground(沿航向) = 3040 px × GSD
    触发间距         = 0.25 × W_ground  （前向重叠 75 %）

  示例（h = 250 m）：GSD 6.5 cm → W_ground 198 m → 间距 49.5 m
                    @ 23 m/s → 每 2.15 s 一帧 → 盘旋 10 min 约 279 帧

  启用方式：SCR_ENABLE=1 / SCR_VM_I_COUNT ≥ 1 / SCR_HEAP_SIZE ≥ 64，
            本文件放 SD 卡 /APM/scripts/。

  ⚠ 状态：示例脚本，**未上机验证**。
  ⚠ **TRIG_PIN 必须按实际板子设置**：在 Mission Planner 把对应 PWM 输出改为 GPIO
     （减小 BRD_PWM_COUNT），再用 `gpio` 绑定写入。对应 [hardware/interface/pinmap.md]
     的 `CAM_TRIG`（示例 PE15）。GPIO 编号以实际固件为准。
]]

local UPDATE_MS = 100           -- 10 Hz，够用且省 CPU

-- 相机与光学参数（[docs/07] 7.4）
local PIXEL_ALONG  = 3040       -- 沿航向像素数（4056×3040 传感器）
local PIXEL_PITCH  = 1.55e-6    -- 像元尺寸（m）
local FOCAL_LEN    = 6.0e-3     -- 焦距（m）
local OVERLAP_FRAC = 0.25       -- 前向重叠 75 % → 相邻帧间距 = 0.25 × 幅宽

local TRIG_PIN     = 51         -- ⚠ 示例值，必须按实际 GPIO 编号替换
local PULSE_MS     = 10         -- 触发脉宽

local dist_accum_m = 0
local frame_count  = 0
local last_ms      = 0
local pulse_until  = 0

-- 当前 AGL（m）；优先用地形跟随的高度，退化为相对 home
local function agl_m()
  local d = ahrs:get_relative_position_D_home()
  if d then return -d end       -- D 向下为正，取反
  return nil
end

local function trigger_spacing_m(h)
  local gsd = h * PIXEL_PITCH / FOCAL_LEN      -- m/px
  return OVERLAP_FRAC * PIXEL_ALONG * gsd      -- m
end

local function update()
  local now = millis()
  local dt  = (last_ms == 0) and 0 or ((now - last_ms) / 1000.0)
  last_ms = now

  -- 脉冲结束后拉低
  if pulse_until > 0 and now >= pulse_until then
    gpio:write(TRIG_PIN, 0)
    pulse_until = 0
  end

  if not vehicle:get_likely_flying() then
    return update, UPDATE_MS
  end

  local h = agl_m()
  local gs = ahrs:groundspeed_vector()
  if not h or not gs then
    return update, UPDATE_MS
  end

  local speed = gs:length()                    -- m/s
  dist_accum_m = dist_accum_m + speed * dt

  local spacing = trigger_spacing_m(h)
  if spacing > 0 and dist_accum_m >= spacing then
    dist_accum_m = dist_accum_m - spacing
    frame_count = frame_count + 1
    gpio:write(TRIG_PIN, 1)                    -- 触发快门
    pulse_until = now + PULSE_MS
    gcs:send_text(6, string.format("CAM: #%d @ %.0f m (spacing %.1f m)",
                                   frame_count, h, spacing))
  end

  return update, UPDATE_MS
end

return update, UPDATE_MS
