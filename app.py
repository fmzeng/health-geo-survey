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
COLUMNS = ["编号", "经度", "纬度", "类型", "状态", "负责人"]

if os.path.exists(DATA_FILE):
    try:
        df = pd.read_csv(DATA_FILE)
        # 补齐缺失列，防止 KeyError
        for c in COLUMNS:
            if c not in df.columns:
                df[c] = ""
    except Exception as e:
        st.warning(f"读取 {DATA_FILE} 失败，已重置为空表：{e}")
        df = pd.DataFrame(columns=COLUMNS)
else:
    df = pd.DataFrame(columns=COLUMNS)

# ========== 侧边栏：添加点位 ==========
st.sidebar.header("➕ 添加调查点位")
with st.sidebar.form("add_form"):
    pid = st.text_input("点位编号", f"HG-{len(df)+1:03d}")
    lon = st.number_input("经度", value=112.938, format="%.6f")
    lat = st.number_input("纬度", value=28.228, format="%.6f")
    ptype = st.selectbox(
        "点位类型",
        ["岩石", "土壤", "地下水", "地表水", "沉积物", "农作物", "血液", "尿液", "人发"]
    )
    status = st.selectbox("采样状态", ["待采样", "已采样", "已送检", "已完成"])
    owner = st.text_input("负责人")
    submitted = st.form_submit_button("添加")

if submitted:
    new_row = pd.DataFrame([{
        "编号": pid, "经度": lon, "纬度": lat,
        "类型": ptype, "状态": status, "负责人": owner
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
    st.sidebar.success(f"已添加 {pid}")
    # 兼容老版本 Streamlit
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

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
            st.success("已保存！请刷新页面查看地图更新。")
            # 可选：保存后刷新，让 df 同步
            # st.rerun()
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
        # 过滤经纬度异常值，防止地图报错
        map_df = df.dropna(subset=["纬度", "经度"])
        map_df = map_df[
            map_df["纬度"].between(-90, 90) &
            map_df["经度"].between(-180, 180)
        ]

        if len(map_df) == 0:
            st.warning("没有有效的经纬度数据，无法绘制地图。")
        else:
            m = folium.Map(
                location=[map_df["纬度"].mean(), map_df["经度"].mean()],
                zoom_start=8
            )
            colors = {
                "待采样": "gray", "已采样": "blue",
                "已送检": "orange", "已完成": "green"
            }
            for _, r in map_df.iterrows():
                folium.Marker(
                    [r["纬度"], r["经度"]],
                    popup=f"{r['编号']} | {r['类型']} | {r['状态']}",
                    tooltip=str(r["编号"]),
                    icon=folium.Icon(color=colors.get(r["状态"], "blue"))
                ).add_to(m)
            st_folium(m, height=550, use_container_width=True)

# ========== 底部统计 ==========
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("点位总数", len(df))
c2.metric("已完成", int((df["状态"] == "已完成").sum()) if len(df) else 0)
c3.metric(
    "完成率",
    f"{(df['状态']=='已完成').mean()*100:.0f}%" if len(df) else "0%"
)
