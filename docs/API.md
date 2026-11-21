# 接口

模块GET使用仓内样例，模块POST可传csv或rows与context，直接计算当前规则。/api/runs使用完整流水线并原子保存。每个阶段返回rows、quarantine、metrics；后续阶段还返回累计隔离。/api/upload接收multipart文件file。/api/runs/<id>/archive只导出一份带清单与证据的CSV。

/api/sections/adjudicate按施工段实际起止区间裁决班次归属，返回互不重叠的签认区间、逐班归属与隔离原因，不落库。/api/sections/basis/switch把裁决结果作为新计量依据原子切换：新依据区间并集未覆盖现行依据时返回409并保留旧签证；同一依据重试返回原结果且idempotent=true，不重复计量。/api/sections/basis返回现行依据与全部历史，/api/sections/basis/<id>回查任一依据（含已被替换的），/api/sections/basis/<id>/sections/<section_id>按施工段回查签认区间与班次来源。
