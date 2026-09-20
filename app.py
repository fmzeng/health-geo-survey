import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import math

# ========== 页面设置 ==========
st.set_page_config(
    page_title="健康地质调查点位布设与采样流程管理软件",
    layout="wide"
)
st.title("🧭 健康地质调查点位布设与采样流程管理软件")

DATA_FILE = "points.csv"

# ========== WGS-84 → GCJ-02 转换 ==========
def wgs84_to_gcj02(lng, lat):
    """WGS-84 转 GCJ-02（高德底图使用）"""
    a = 6378245.0
    ee = 0.00669342162296594323

    def transform_lat(x, y):
        ret = -100.0 + 2.0*x + 3.0*y + 0.2*y*y + 0.1*x*y + 0.2*math.sqrt(abs(x))
        ret += (20.0*math.sin(6.0*x*math.pi) + 20.0*math.sin(2.0*x*math.pi)) * 2.0/3.0
        ret += (20.0*math.sin(y*math.pi) + 40.0*math.sin(y/3.0*math.pi)) * 2.0/3.0
        ret += (160.0*math.sin(y/12.0*math.pi) + 320*math.sin(y*math.pi/30.0)) * 2.0/3.0
        return ret

    def transform_lng(x, y):
        ret = 300.0 + x + 2.0*y + 0.1*x*x + 0.1*x*y + 0.1*math.sqrt(abs(x))
        ret += (20.0*math.sin(6.0*x*math.pi) + 20.0*math.sin(2.0*x*math.pi)) * 2.0/3.0
        ret += (20.0*math.sin(x*math.pi) + 40.0*math.sin(x/3.0*math.pi)) * 2.0/3.0
        ret += (150.0*math.sin(x/12.0*math.pi) + 300.0*math.sin(x/30.0*math.pi)) * 2.0/3.0
        return ret

    dlat = transform_lat(lng - 105.0, lat - 35.0)
    dlng = transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lng + dlng, lat + dlat

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
    st.subheader("调查点位分布地图（底图：高德地图，数据坐标系：WGS-84）")
    if len(df) == 0:
        st.info("暂无点位，请先在左侧添加。")
    else:
        # 用第一个点的 GCJ-02 坐标做地图中心
        center_lng, center_lat = wgs84_to_gcj02(
            df["经度"].mean(), df["纬度"].mean()
        )
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=8,
            tiles=None,          # 关闭默认底图
            control_scale=True
        )

        # 高德矢量路网底图
        folium.TileLayer(
            tiles='https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
            subdomains=['1', '2', '3', '4'],
            attr='高德地图',
            name='高德地图',
            overlay=False,
            control=True
        ).add_to(m)

        # 高德卫星影像底图（可选切换）
        folium.TileLayer(
            tiles='https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}',
            subdomains=['1', '2', '3', '4'],
            attr='高德卫星',
            name='高德卫星',
            overlay=False,
            control=True
        ).add_to(m)

        colors = {
            "待采样": "gray", "已采样": "blue",
            "已送检": "orange", "已完成": "green"
        }

        for _, r in df.iterrows():
            # 关键：绘制前把 WGS-84 转成 GCJ-02，避免偏移
            gcj_lng, gcj_lat = wgs84_to_gcj02(r["经度"], r["纬度"])
            folium.Marker(
                [gcj_lat, gcj_lng],
                popup=f"{r['编号']} | {r['类型']} | {r['状态']}",
                tooltip=r["编号"],
                icon=folium.Icon(color=colors.get(r["状态"], "blue"))
            ).add_to(m)

        folium.LayerControl().add_to(m)
        st_folium(m, width=None, height=550)

# ========== 底部统计 ==========
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("点位总数", len(df))
c2.metric("已完成", (df["状态"] == "已完成").sum() if len(df) else 0)
c3.metric("完成率",
          f"{(df['状态']=='已完成').mean()*100:.0f}%" if len(df) else "0%")
