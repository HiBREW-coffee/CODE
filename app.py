import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io

# 1. 页面基本配置
st.set_page_config(page_title="HiBREW 大促 Code 自动匹配系统", layout="wide")
st.title("🚀 AliExpress 大促 Code 智能匹配工具")
st.caption("上传大促规则图与产品底价清单，一键生成主图排版表格")

# 2. 侧边栏：配置 API Key
st.sidebar.header("⚙️ 账户配置")
api_key = st.sidebar.text_input("请输入 Gemini API Key:", type="password")

if not api_key:
    st.info("💡 请在左侧输入您的 Gemini API Key 以激活 AI 计算引擎。")
    st.stop()

# 初始化 AI 模型
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-pro') # 推荐使用 Pro 模型处理复杂的长图和表格

# 3. 主界面：上传大促规则
st.header("1. 上传大促官方规则")
rule_file = st.file_uploader("请上传官方 Code 集合长图或规则 Excel (支持 JPG/PNG)", type=["jpg", "png", "jpeg"])

if rule_file:
    image = Image.open(rule_file)
    st.image(image, caption="已成功加载大促规则图", max_width=400)

# 4. 主界面：输入/上传产品价格
st.header("2. 输入产品底价清单")
tab1, tab2 = st.tabs(["💬 手动粘贴文本", "📊 上传 Excel/CSV 文件"])

product_data = ""

with tab1:
    product_text = st.text_area(
        "请按格式输入（机型 - 价格），每行一个。例如：\nH10A - $75\nH10B - $145\nH16 - $210",
        height=150
    )
    if product_text:
        product_data = product_text

with tab2:
    excel_file = st.file_uploader("上传包含机型和美元价格的表格", type=["xlsx", "xls", "csv"])
    if excel_file:
        if excel_file.name.endswith('csv'):
            df_input = pd.read_csv(excel_file)
        else:
            df_input = pd.read_excel(excel_file)
        st.write("已读取到的产品清单：", df_input.head())
        # 将表格转为纯文本喂给 AI 提炼
        product_data = df_input.to_string(index=False)

# 5. 触发计算
st.header("3. 开始智能匹配")
if st.button("🔮 一键生成全店 Code 矩阵表", type="primary"):
    if not rule_file or not product_data:
        st.error("❌ 请确保您已上传大促规则图，并提供了产品底价清单！")
    else:
        with st.spinner("AI 正在解析长图、换算最新汇率并为您疯狂匹配中... 请稍候..."):
            try:
                # 构造 Prompt
                prompt = f"""
                你是一个专业的跨境电商大促计算专家。
                请仔细阅读这张大促规则图片，提取出所有国家、货币门槛和对应的 Code。
                然后根据以下提供的产品底价清单（通常为美元售价），使用最新的实时汇率换算为各目标国货币。
                在规则库中，寻找该价格能满足的【最高门槛档位】，并提取对应的 Code。
                
                产品底价清单如下：
                {product_data}
                
                请直接以 Markdown 表格的形式输出最终结果。
                表格第一列为 机型 / SKU，第二列为基础售价，后续列分别为各个国家的 Code。
                格式要求极其干净，方便设计师直接复制。如果未达最低门槛，请填写“-”。
                不要输出任何前言和后记。
                """
                
                # 调用 Gemini 视觉模型
                response = model.generate_content([prompt, image])
                
                # 展示结果
                st.success("🎉 匹配完成！")
                st.markdown(response.text)
                
                # 提供复制提示
                st.info("☝️ 您可以直接框选上方的表格，复制粘贴到 Excel 或直接截图发送给设计团队。")
                
            except Exception as e:
                st.error(f"发生错误: {str(e)}")
