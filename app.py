import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

# ========== 页面设置 ==========
st.set_page_config(
    page_title="健康地质调查点位布设与采样流程管理软件",
    layout="wide"
)
st.title("🧭 健康地质调查点位布设与采样流程管理软件")

DATA_FILE = "points.csv"

# ========== 读取数据 ==========
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
else:
    df = pd.DataFrame(columns=["编号", "经度", "纬度", "类型", "状态", "负责人"])

# ========== 侧边栏：添加点位 ==========
st.sidebar.header("➕ 添加调查点位")
with st.sidebar.form("add_form"):
    pid = st.text_input("点位编号", f"HG-{len(df)+1:03d}")
    lon = st.number_input("经度", value=112.938, format="%.6f")
    lat = st.number_input("纬度", value=28.228, format="%.6f")
    ptype = st.selectbox("点位类型", ["岩石","土壤", "沉积物","地表水", "地下水", "血液","尿液","人发"])
    status = st.selectbox("采样状态", ["待采样", "已采样", "已送检", "已完成"])
    owner = st.text_input("负责人")
    if st.form_submit_button("添加"):
        df = pd.concat([df, pd.DataFrame([{
            "编号": pid, "经度": lon, "纬度": lat,
            "类型": ptype, "状态": status, "负责人": owner
        }])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
        st.sidebar.success(f"已添加 {pid}")
        st.rerun()

# ========== 主界面：两个标签页 ==========
tab1, tab2 = st.tabs(["📋 点位管理", "🗺️ 地图可视化"])

# ---- Tab1：表格编辑 ----
with tab1:
    st.subheader("点位数据表（可直接编辑、删除）")
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存修改"):
            edited.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
            st.success("已保存！")
    with col2:
        st.download_button(
            "⬇️ 导出CSV",
            edited.to_csv(index=False).encode("utf-8-sig"),
            "points.csv", "text/csv"
        )

# ---- Tab2：地图 ----
with tab2:
    st.subheader("调查点位分布地图")
    if len(df) == 0:
        st.info("暂无点位，请先在左侧添加。")
    else:
       import folium

# 创建地图，location 传入 WGS-84 坐标（经度, 纬度）
m = folium.Map(
    location=[28.2278, 112.9388],  # 长沙，WGS-84
    zoom_start=10,
    tiles=None,                     # 关闭默认底图
    control_scale=True
)

# 添加高德地图底图（矢量路网）
folium.TileLayer(
    tiles='https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
    subdomains=['1', '2', '3', '4'],
    attr='高德地图',
    name='高德地图',
    overlay=False,
    control=True
).add_to(m)

# 添加高德卫星影像（可选）
folium.TileLayer(
    tiles='https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}',
    subdomains=['1', '2', '3', '4'],
    attr='高德卫星',
    name='高德卫星',
    overlay=False,
    control=True
).add_to(m)

folium.LayerControl().add_to(m)
m.save('健康地质图.html')
        colors = {
            "待采样": "gray", "已采样": "blue",
            "已送检": "orange", "已完成": "green"
        }
        for _, r in df.iterrows():
            folium.Marker(
                [r["纬度"], r["经度"]],
                popup=f"{r['编号']} | {r['类型']} | {r['状态']}",
                tooltip=r["编号"],
                icon=folium.Icon(color=colors.get(r["状态"], "blue"))
            ).add_to(m)
        st_folium(m, width=None, height=550)

# ========== 底部统计 ==========
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("点位总数", len(df))
c2.metric("已完成", (df["状态"] == "已完成").sum() if len(df) else 0)
c3.metric("完成率",
          f"{(df['状态']=='已完成').mean()*100:.0f}%" if len(df) else "0%")
