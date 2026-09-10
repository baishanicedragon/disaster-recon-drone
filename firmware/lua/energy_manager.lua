--[[
  energy_manager.lua · 能量管理（强制返航判据）

  作用：实时估算"飞回回收场还需要多少能量"，余量不足则**立即强制返航**，
        不等盘旋段（LOITER）自然结束。

  启用方式（ArduPilot Lua scripting，4.6+）：
    1) SCR_ENABLE = 1（重启生效）
    2) SCR_VM_I_COUNT ≥ 1（每个脚本一个虚拟机）
    3) SCR_HEAP_SIZE ≥ 64（KB）
    4) 本文件放飞控 SD 卡的 /APM/scripts/ 目录

  ⚠ 状态：示例脚本，**未上机验证**。API 以 ArduPilot 官方最新文档为准。
  ⚠ 本脚本只做"强制返航"这一种动作；**不替代** docs/12 的地面能量核算。

  判据（[docs/08] RETURN_MARGIN = 1.15）：
    E_need  = 返航距离 × 巡航能耗 + 返航爬升能量 + 航电基线 × 预计剩余时间
    E_avail = 电池剩余可用容量
    E_avail < E_need × 1.15  →  强制返航
]]

local UPDATE_MS   = 1000        -- 1 Hz

-- 常量（来源见右；随构型版本更新）
local CRUISE_WH_PER_KM = 7.44   -- v0.4 双翼巡航能耗（README 第 4 节）
local CRUISE_KMH       = 100.8  -- 28 m/s
local RETURN_MARGIN    = 1.15   -- [docs/08] 逆风余量
local AVIONICS_W       = 60     -- 航电基线功率（[docs/07] 7.7）
local CLIMB_M          = 950    -- 返航需爬升高度（README）
local MASS_KG          = 12.93  -- MTOW（README）
local PROP_EFF         = 0.60   -- 爬升能量换算效率（粗估，需实测标定）
local PACK_WH          = 778    -- 12S4P 电池（README）
local USABLE_FRAC      = 0.80   -- 可用深度（README：778 × 80% = 622 Wh）
local RTL_MODE         = 11     -- Plane RTL 模式编号（**以实际固件 mode.h 为准**）

local warned = false

-- 爬升所需能量（Wh）：m·g·h 换算成 Wh 并除以效率
local function climb_energy_wh(m_kg, h_m)
  return (m_kg * 9.81 * h_m) / 3600.0 / PROP_EFF
end

-- 当前位置到 home 的地面距离（m）
local function dist_home_m()
  local home = ahrs:get_home()
  local cur  = ahrs:get_position()
  if not home or not cur then return nil end
  return cur:get_distance(home)
end

local function update()
  -- 只在自动模式下生效；手动/测试时不管
  if not vehicle:get_likely_flying() then
    return update, UPDATE_MS
  end

  local d_m = dist_home_m()
  local pct = battery:capacity_remaining_pct(0)
  if not d_m or not pct then
    return update, UPDATE_MS
  end

  local d_km   = d_m / 1000.0
  local t_h    = d_km / CRUISE_KMH

  local e_need = d_km * CRUISE_WH_PER_KM        -- 返航巡航
               + climb_energy_wh(MASS_KG, CLIMB_M)  -- 返航爬升
               + AVIONICS_W * t_h               -- 航电基线
  local e_avail = PACK_WH * USABLE_FRAC * (pct / 100.0)

  if e_avail < e_need * RETURN_MARGIN then
    if not warned then
      gcs:send_text(2, string.format(
        "ENERGY: force RTL (need %.0f Wh, avail %.0f Wh)", e_need, e_avail))
      warned = true
    end
    if vehicle:get_mode() ~= RTL_MODE then
      vehicle:set_mode(RTL_MODE)
    end
  else
    warned = false
  end

  return update, UPDATE_MS
end

return update, UPDATE_MS
