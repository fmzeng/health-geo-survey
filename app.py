import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
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

# 状态 → 颜色 配置
STATUS_COLORS = {
    "待采样": "gray",
    "已采样": "blue",
    "已送检": "orange",
    "已完成": "green",
}

# ========== 坐标系转换 ==========
def out_of_china(lng, lat):
    """判断是否在中国境外（境外不做偏移）"""
    return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)

def _transform_lat(x, y):
    ret = -100.0 + 2.0*x + 3.0*y + 0.2*y*y + 0.1*x*y + 0.2*math.sqrt(abs(x))
    ret += (20.0*math.sin(6.0*x*math.pi) + 20.0*math.sin(2.0*x*math.pi)) * 2.0/3.0
    ret += (20.0*math.sin(y*math.pi) + 40.0*math.sin(y/3.0*math.pi)) * 2.0/3.0
    ret += (160.0*math.sin(y/12.0*math.pi) + 320*math.sin(y*math.pi/30.0)) * 2.0/3.0
    return ret

def _transform_lng(x, y):
    ret = 300.0 + x + 2.0*y + 0.1*x*x + 0.1*x*y + 0.1*math.sqrt(abs(x))
    ret += (20.0*math.sin(6.0*x*math.pi) + 20.0*math.sin(2.0*x*math.pi)) * 2.0/3.0
    ret += (20.0*math.sin(x*math.pi) + 40.0*math.sin(x/3.0*math.pi)) * 2.0/3.0
    ret += (150.0*math.sin(x/12.0*math.pi) + 300.0*math.sin(x/30.0*math.pi)) * 2.0/3.0
    return ret

def wgs84_to_gcj02(lng, lat):
    """WGS-84 转 GCJ-02"""
    if out_of_china(lng, lat):
        return lng, lat
    a = 6378245.0
    ee = 0.00669342162296594323
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lng + dlng, lat + dlat

def gcj02_to_bd09(lng, lat):
    """GCJ-02 转 BD-09"""
    x_pi = math.pi * 3000.0 / 180.0
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * x_pi)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * x_pi)
    bd_lng = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    return bd_lng, bd_lat

def wgs84_to_bd09(lng, lat):
    """WGS-84 转 BD-09（百度底图使用）"""
    if out_of_china(lng, lat):
        return lng, lat
    gcj_lng, gcj_lat = wgs84_to_gcj02(lng, lat)
    return gcj02_to_bd09(gcj_lng, gcj_lat)

# ========== 读取数据（含异常处理）==========
def load_data():
    cols = ["编号", "经度", "纬度", "类型", "状态", "负责人"]
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            # 确保列齐全
            for c in cols:
                if c not in df.columns:
                    df[c] = None
            return df[cols]
        except Exception as e:
            st.warning(f"读取 {DATA_FILE} 失败，已新建空表。原因：{e}")
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

df = load_data()

# ========== 侧边栏：添加点位 ==========
st.sidebar.header("➕ 添加调查点位")
with st.sidebar.form("add_form"):
    pid = st.text_input("点位编号", f"HG-{len(df)+1:03d}")
    lon = st.number_input("经度", value=112.938, format="%.6f",
                          min_value=-180.0, max_value=180.0)
    lat = st.number_input("纬度", value=28.228, format="%.6f",
                          min_value=-90.0, max_value=90.0)
    ptype = st.selectbox(
        "点位类型",
        ["岩石", "土壤", "沉积物", "地表水", "地下水", "血液", "尿液", "人发"]
    )
    status = st.selectbox("采样状态", list(STATUS_COLORS.keys()))
    owner = st.text_input("负责人")
    submitted = st.form_submit_button("添加")

    if submitted:
        # 编号唯一性检查
        if pid in df["编号"].astype(str).values:
            st.sidebar.error(f"编号 {pid} 已存在，请更换。")
        else:
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
    st.subheader("调查点位分布地图（底图：百度地图，数据坐标系：WGS-84）")
    if len(df) == 0:
        st.info("暂无点位，请先在左侧添加。")
    else:
        # 地图中心：先转 BD-09
        center_lng, center_lat = wgs84_to_bd09(
            df["经度"].mean(), df["纬度"].mean()
        )
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=8,
            tiles=None,          # 关闭默认底图
            control_scale=True
        )

        # 百度矢量底图
        folium.TileLayer(
            tiles='http://online{s}.map.bdimg.com/onlinelabel/?qt=tile&x={x}&y={y}&z={z}&styles=pl&scaler=1&p=1',
            subdomains=['0', '1', '2', '3'],
            attr='百度地图',
            name='百度地图',
            overlay=False,
            control=True
        ).add_to(m)

        # 百度卫星底图
        folium.TileLayer(
            tiles='http://shangetu{s}.map.bdimg.com/it/u=x={x};y={y};z={z};v=009;type=sate&fm=46',
            subdomains=['0', '1', '2', '3'],
            attr='百度卫星',
            name='百度卫星',
            overlay=False,
            control=True
        ).add_to(m)

        # 点位聚合
        marker_cluster = MarkerCluster(name="调查点位").add_to(m)

        for _, r in df.iterrows():
            try:
                lng = float(r["经度"])
                lat = float(r["纬度"])
            except (TypeError, ValueError):
                continue  # 跳过无效坐标

            # 关键：WGS-84 → BD-09
            bd_lng, bd_lat = wgs84_to_bd09(lng, lat)

            folium.Marker(
                [bd_lat, bd_lng],
                popup=f"{r['编号']} | {r['类型']} | {r['状态']}",
                tooltip=str(r["编号"]),
                icon=folium.Icon(color=STATUS_COLORS.get(r["状态"], "blue"))
            ).add_to(marker_cluster)

        folium.LayerControl().add_to(m)
        st_folium(m, width=None, height=550)

# ========== 底部统计 ==========
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("点位总数", len(df))
c2.metric("已完成", (df["状态"] == "已完成").sum() if len(df) else 0)
c3.metric("完成率",
          f"{(df['状态']=='已完成').mean()*100:.0f}%" if len(df) else "0%")
