--[[
  abort_logic.lua · 中止判据（段 II 改平失败 → 机头朝下迫降备用剖面）

  依据 [docs/07] 7.2.2 段 3：
    "门控：空速 ≥ 1.1 Vs（20.6 m/s）且高度 ≥ 90 m → 解锁机翼展开（硬件互锁）
     任一不满足 → 放弃改平，进入『机头朝下迫降』备用剖面"

  本脚本监控两件事：
    1) **改平窗口用尽**：高度已跌破 h_deploy_min × 0.5 仍未撑开 → 强制备用剖面；
    2) **GNSS 长时间丢失**：> 120 s 无 3D 定位 → 告警（[docs/02]：120 s 内航位误差 < 60 m）。

  启用方式：SCR_ENABLE=1 / SCR_VM_I_COUNT ≥ 1 / SCR_HEAP_SIZE ≥ 64，
            本文件放 SD 卡 /APM/scripts/。

  ⚠ 状态：示例脚本，**未上机验证**。
  ⚠ `wings_deployed()` 的实现**必须由自定义固件或 IL 硬件信号提供**——
     纯软件判定位不可靠，见 [hardware/interface/pinmap.md] 的 `IL_DEPLOY_OK` /
     `IL_WING_LOCK_L/R`（断线 → 判未锁定）。下面给出的是接口占位。
]]

local UPDATE_MS = 200          -- 5 Hz

-- 从 SCR_USER 读门控阈值（见 ardupilot/params/README.md）
local VS_THRESH    = param:get('SCR_USER1') or 20.9   -- 撑开门控空速
local H_DEPLOY_MIN = param:get('SCR_USER2') or 90     -- 撑开门控最低高度
local GNSS_LOST_S  = 120                              -- [docs/02] 航位推算窗口

local ABORT_MODE   = 11        -- 示例：Plane RTL；实际"机头朝下迫降"需自定义模式
                               -- ⚠ 备用剖面是**自定义状态机**，编号以实际固件为准

local gnss_lost_ms = 0
local last_ms      = 0
local aborted      = false

--- 机翼是否已撑开锁定。
--  实际实现：读 `IL_WING_LOCK_L/R`（常闭微动，断线即判未锁）或自定义固件状态字。
--  这里返回 nil 表示"信号不可用"，调用方按保守处理。
local function wings_deployed()
  -- TODO: 接入 IL 硬件信号。示例：
  --   return gpio:read(PIN_WING_LOCK_L) == 1 and gpio:read(PIN_WING_LOCK_R) == 1
  return nil
end

local function agl_m()
  local d = ahrs:get_relative_position_D_home()
  if d then return -d end
  return nil
end

local function update()
  local now = millis()
  local dt  = (last_ms == 0) and 0 or ((now - last_ms) / 1000.0)
  last_ms = now

  if not vehicle:get_likely_flying() then
    gnss_lost_ms = 0
    return update, UPDATE_MS
  end

  -- (1) 改平窗口用尽 → 放弃改平
  local h = agl_m()
  local deployed = wings_deployed()
  if h and not aborted and deployed == false and h < H_DEPLOY_MIN * 0.5 then
    gcs:send_text(2, string.format(
      "ABORT: deploy window lost (h=%.0f m < %.0f m) -> nose-down profile",
      h, H_DEPLOY_MIN * 0.5))
    vehicle:set_mode(ABORT_MODE)
    aborted = true
  end

  -- (2) GNSS 丢失计时
  if gps:status(0) >= 3 then            -- 3 = 3D fix
    gnss_lost_ms = 0
  else
    gnss_lost_ms = gnss_lost_ms + (dt * 1000)
    if gnss_lost_ms > GNSS_LOST_S * 1000 then
      gcs:send_text(3, string.format("NAV: GNSS lost %.0f s (DR only)", gnss_lost_ms/1000))
      -- 此处只告警：航位推算仍在窗口内（[docs/02] 120 s / < 60 m）
      -- 超出窗口后的处置由飞控失效保护与 docs/12 流程决定
    end
  end

  return update, UPDATE_MS
end

return update, UPDATE_MS
