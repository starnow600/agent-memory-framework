# atom-point-in-time-calculation

## Trigger
涉及损失/收益/规避金额的计算时

## Rule
必须明确point-in-time计算口径：一次性计算 vs 累加计算、基准日期、计价时点。两种口径不可混用。发现偏差时立即修正全链路（MEMORY+Wiki+脚本+TOOLS同步）。

## Why
7/17规避损失计算出现60,138 vs 14,583的3倍偏差。根因：累加计算（每日新增的累加值）与point-in-time一次性计算（卖出价vs当日收盘的差值）两种口径混用。60,138是错误累加值，14,583是正确的一次性计算值。偏差传播到MEMORY.md和Wiki。

## Source
7/17 规避损失累加错误修正（60,138→14,583）
