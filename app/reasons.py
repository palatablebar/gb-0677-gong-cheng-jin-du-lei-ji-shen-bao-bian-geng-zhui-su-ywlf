REASONS={"BAD_COLUMNS":"列数不匹配","EMPTY_VALUE":"必填值为空","INVALID_NUMBER":"数字格式错误","INVALID_TIME":"时间缺少偏移或格式错误","DUPLICATE_CONFLICT":"同键取值冲突","UNKNOWN_REFERENCE":"引用不存在","STALE_VERSION":"版本已更新","EMPTY_FILE":"文件为空","HEADER_ONLY":"仅有表头","BLANK_ONLY":"全部为空行","INVALID_DATE":"日期格式错误","BAD_SECTIONS":"施工段定义无效","BAD_SHIFTS":"班次记录无效","DUPLICATE_SECTION":"施工段编号重复","BAD_INTERVAL":"施工段区间无效","BAD_POLICY":"交叠裁决策略无效","NO_SECTION_COVER":"班次无施工段覆盖","INTERVAL_OVERLAP":"签认区间交叠","SWITCH_GAP":"切换会遗留无依据区间","BASIS_CONFLICT":"依据标识冲突"}
def reject(row, code, detail):
    return {**row,"reason":code,"detail":detail}
def sources(row):
    return row.get("_sources", [row.get("_line",0)])
