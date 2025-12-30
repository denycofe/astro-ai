import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, time
from kerykeion import AstrologicalSubject, SynastryAspects

# ==============================================================================
# ⚙️ 1. 安全配置区
# ==============================================================================

try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except (FileNotFoundError, KeyError):
    DEEPSEEK_API_KEY = ""

# ==============================================================================
# 🏙️ 2. 城市经纬度数据库 (拼音增强版 - 支持搜索)
# ==============================================================================
CITY_DB = {
    # --- 直辖市 ---
    "北京 (Beijing)": {"lat": 39.90, "lng": 116.40},
    "上海 (Shanghai)": {"lat": 31.23, "lng": 121.47},
    "天津 (Tianjin)": {"lat": 39.08, "lng": 117.20},
    "重庆 (Chongqing)": {"lat": 29.56, "lng": 106.55},

    # --- 华东 ---
    "南京 (Nanjing)": {"lat": 32.06, "lng": 118.79}, "苏州 (Suzhou)": {"lat": 31.30, "lng": 120.58},
    "无锡 (Wuxi)": {"lat": 31.49, "lng": 120.31}, "常州 (Changzhou)": {"lat": 31.81, "lng": 119.97},
    "杭州 (Hangzhou)": {"lat": 30.27, "lng": 120.15}, "宁波 (Ningbo)": {"lat": 29.86, "lng": 121.52},
    "温州 (Wenzhou)": {"lat": 27.99, "lng": 120.70}, "合肥 (Hefei)": {"lat": 31.82, "lng": 117.23},
    "福州 (Fuzhou)": {"lat": 26.07, "lng": 119.30}, "厦门 (Xiamen)": {"lat": 24.48, "lng": 118.09},
    "泉州 (Quanzhou)": {"lat": 24.87, "lng": 118.67}, "南昌 (Nanchang)": {"lat": 28.68, "lng": 115.85},
    "济南 (Jinan)": {"lat": 36.65, "lng": 117.12}, "青岛 (Qingdao)": {"lat": 36.06, "lng": 120.38},
    
    # --- 华南 ---
    "广州 (Guangzhou)": {"lat": 23.13, "lng": 113.26}, "深圳 (Shenzhen)": {"lat": 22.54, "lng": 114.06},
    "珠海 (Zhuhai)": {"lat": 22.27, "lng": 113.57}, "佛山 (Foshan)": {"lat": 23.02, "lng": 113.12},
    "东莞 (Dongguan)": {"lat": 23.02, "lng": 113.75}, "南宁 (Nanning)": {"lat": 22.81, "lng": 108.37},
    "海口 (Haikou)": {"lat": 20.04, "lng": 110.33}, "三亚 (Sanya)": {"lat": 18.25, "lng": 109.51},
    
    # --- 华中 ---
    "武汉 (Wuhan)": {"lat": 30.59, "lng": 114.30}, "长沙 (Changsha)": {"lat": 28.23, "lng": 112.93},
    "郑州 (Zhengzhou)": {"lat": 34.75, "lng": 113.62}, "洛阳 (Luoyang)": {"lat": 34.62, "lng": 112.45},
    
    # --- 华北/东北 ---
    "石家庄 (Shijiazhuang)": {"lat": 38.04, "lng": 114.51}, "太原 (Taiyuan)": {"lat": 37.87, "lng": 112.55},
    "沈阳 (Shenyang)": {"lat": 41.80, "lng": 123.43}, "大连 (Dalian)": {"lat": 38.91, "lng": 121.61},
    "长春 (Changchun)": {"lat": 43.81, "lng": 125.32}, "哈尔滨 (Harbin)": {"lat": 45.80, "lng": 126.53},
    
    # --- 西南/西北 ---
    "成都 (Chengdu)": {"lat": 30.57, "lng": 104.06}, "贵阳 (Guiyang)": {"lat": 26.65, "lng": 106.63},
    "昆明 (Kunming)": {"lat": 25.05, "lng": 102.72}, "西安 (Xian)": {"lat": 34.34, "lng": 108.94},
    "兰州 (Lanzhou)": {"lat": 36.06, "lng": 103.83}, "乌鲁木齐 (Urumqi)": {"lat": 43.82, "lng": 87.62},
    
    # --- 港澳台 ---
    "香港 (Hong Kong)": {"lat": 22.32, "lng": 114.17}, "澳门 (Macau)": {"lat": 22.19, "lng": 113.54},
    "台北 (Taipei)": {"lat": 25.03, "lng": 121.56},
    "其他 (Default)": {"lat": 31.23, "lng": 121.47}
}

# ==============================================================================
# 🧠 3. 核心算法区
# ==============================================================================

ORB_LIMITS = {'conjunction': 8, 'opposition': 6, 'trine': 6, 'square': 4, 'sextile': 4}
DIMENSION_MAP = {
    ('Venus', 'Mars'): 'P', ('Mars', 'Venus'): 'P', ('Sun', 'Mars'): 'P', ('Mars', 'Sun'): 'P',
    ('Mercury', 'Mercury'): 'C', ('Mercury', 'Moon'): 'C', ('Moon', 'Mercury'): 'C',
    ('Sun', 'Moon'): 'S', ('Moon', 'Sun'): 'S', ('Saturn', 'Venus'): 'S', ('Venus', 'Saturn'): 'S', ('Saturn', 'Moon'): 'S',
    ('Sun', 'Sun'): 'V', ('Venus', 'Venus'): 'V', ('Moon', 'Moon'): 'V'
}
PLANET_NATURE = {
    'Benefic': ['Sun', 'Moon', 'Venus', 'Jupiter'],
    'Malefic': ['Mars', 'Saturn', 'Uranus', 'Neptune', 'Pluto'],
    'Neutral': ['Mercury']
}
EXPERT_INTERPRETATIONS = {
    ('Mars', 'Saturn', 'square'): "【高危】踩油门遇上拉手刹，长期压抑易爆发冷暴力。",
    ('Mars', 'Saturn', 'opposition'): "【高危】硬碰硬，土星的冷漠会把火星逼疯。",
    ('Sun', 'Moon', 'conjunction'): "【天作之合】夫唱妇随，灵魂高度共鸣，顶级配置。",
    ('Venus', 'Mars', 'conjunction'): "【干柴烈火】性吸引力爆表，见面就想扑倒。",
    ('Mercury', 'Mercury', 'conjunction'): "【脑回路同步】不需要解释，聊天永远不冷场。"
}

def get_planet_nature(p):
    if p in PLANET_NATURE['Benefic']: return 'Benefic'
    if p in PLANET_NATURE['Malefic']: return 'Malefic'
    return 'Neutral'

def get_expert_guidance(p1, p2, aspect):
    key1, key2 = (p1, p2, aspect), (p2, p1, aspect)
    expert = EXPERT_INTERPRETATIONS.get(key1) or EXPERT_INTERPRETATIONS.get(key2)
    if expert: return f"🌟专家铁律：{expert}"
    t1, t2 = get_planet_nature(p1), get_planet_nature(p2)
    if t1 == 'Malefic' and t2 == 'Malefic' and aspect in ['square', 'opposition']:
        return "⚠️风险提示：双凶星困难相位，存在深层冲突。"
    elif t1 == 'Benefic' and t2 == 'Benefic' and aspect in ['conjunction', 'trine']:
        return "✨吉象提示：双吉星共振，相处轻松愉快。"
    return ""

def get_sign_keyword(planet, sign):
    short_sign = sign[:3].capitalize()
    keywords = {
        'Sun': {'Leo': '舞台主角', 'Ari': '冲动直球', 'Sco': '高冷腹黑', 'Cap': '工作机器', 'Lib': '端水大师', 'Vir': '细节控', 'Gem': '吃瓜群众', 'Tau': '固执金牛', 'Can': '护短狂魔', 'Sag': '自由灵魂', 'Aqu': '外星人', 'Pis': '造梦师'},
        'Moon': {'Leo': '傲娇怪', 'Ari': '急躁小孩', 'Sco': '查岗狂魔', 'Pis': '脑补帝', 'Cap': '忍者神龟', 'Vir': '挑刺王', 'Lib': '纠结伦', 'Gem': '话痨', 'Tau': '美食家', 'Can': '玻璃心', 'Sag': '不回家', 'Aqu': '冷得像风'},
        'Venus': {'Leo': '女神范', 'Sco': '性感神秘', 'Gem': '有趣灵魂', 'Ari': '飒爽', 'Tau': '富婆', 'Can': '贤惠', 'Vir': '清纯', 'Lib': '颜控', 'Sag': '玩伴', 'Cap': '强人', 'Aqu': '酷盖', 'Pis': '软妹'},
        'Mars': {'Leo': '霸总', 'Sco': '深情种', 'Ari': '猛男', 'Cap': '权贵', 'Lib': '绅士', 'Vir': '斯文败类', 'Gem': '弟弟', 'Tau': '老实人', 'Can': '暖男', 'Sag': '阳光男', 'Aqu': '极客', 'Pis': '艺术家'}
    }
    return keywords.get(planet, {}).get(short_sign, f"{short_sign}特质")

def calculate_commercial_score(aspects):
    scores = {'P': 0, 'C': 0, 'S': 0, 'V': 0}
    ENERGY = {'conjunction': 10, 'opposition': 8, 'trine': 8, 'square': 6, 'sextile': 4}
    
    filtered_aspects = []
    for item in aspects:
        p1, p2, asp = item['p1_name'], item['p2_name'], item['aspect']
        orb_limit = ORB_LIMITS.get(asp, 0)
        
        if item['orbit'] <= orb_limit:
            filtered_aspects.append(item)
            dim = DIMENSION_MAP.get((p1, p2)) or DIMENSION_MAP.get((p2, p1))
            if dim and asp in ENERGY:
                scores[dim] += ENERGY[asp]
                if get_planet_nature(p1) == 'Benefic' and get_planet_nature(p2) == 'Benefic':
                    scores[dim] += 2

    final_radar = {}
    for dim, raw in scores.items():
        if raw == 0: final_radar[dim] = 60
        else: final_radar[dim] = min(99, 65 + int(raw * 1.5))
    
    total = int(final_radar['P']*0.3 + final_radar['C']*0.2 + final_radar['S']*0.3 + final_radar['V']*0.2)
    return total, final_radar, filtered_aspects

def call_ai_writer(prompt, api_key):
    if not api_key: return "⚠️ 未配置 API Key，无法生成报告。"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": "你是一位毒舌但专业的占星恋爱军师。"}, {"role": "user", "content": prompt}],
        "temperature": 1.3
    }
    try:
        res = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=120)
        if res.status_code == 200: return res.json()['choices'][0]['message']['content']
        return f"AI 接口报错: {res.text}"
    except Exception as e:
        return f"网络请求失败: {e}"

# ==============================================================================
# 🎨 4. 前端界面 (UI)
# ==============================================================================

st.set_page_config(page_title="AI 恋爱鉴定局", page_icon="🔮", layout="centered")

# CSS 美化
st.markdown("""
    <style>
    .stButton>button { width: 100%; background-color: #FF4B4B; color: white; height: 50px; border-radius: 10px; font-weight: bold; font-size: 18px;}
    .score-box { background: linear-gradient(135deg, #FF9A9E 0%, #FECFEF 100%); padding: 20px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    </style>
""", unsafe_allow_html=True)

st.title("🔮 AI 毒舌恋爱鉴定")
st.caption("大数据 × 占星算法 × 深度求索 AI")

# 手动输入 Key (如果在 Secrets 里没找到)
if not DEEPSEEK_API_KEY:
    with st.sidebar:
        st.warning("⚠️ 未检测到 secrets.toml")
        DEEPSEEK_API_KEY = st.text_input("请输入 DeepSeek API Key", type="password")

with st.form("input_form"):
    col1, col2 = st.columns(2)
    
    current_year = datetime.now().year
    min_date = datetime(1930, 1, 1)
    max_date = datetime(current_year, 12, 31)

    with col1:
        st.subheader("主角 A (自己)")
        name_a = st.text_input("姓名/昵称", value="", placeholder="必填", key="na")
        date_a = st.date_input("出生日期", min_value=min_date, max_value=max_date, value=None, key="da")
        time_a = st.time_input("出生时间 (不清楚填12:00)", value=time(12, 0), key="ta")
        city_name_a = st.selectbox("出生城市", list(CITY_DB.keys()), index=None, placeholder="可输入拼音搜索 (如 Wuhan)", key="ca")
        gender_a = st.selectbox("性别", ["male", "female"], format_func=lambda x: "男生" if x=="male" else "女生", key="ga")

    with col2:
        st.subheader("主角 B (对象)")
        name_b = st.text_input("姓名/昵称", value="", placeholder="必填", key="nb")
        date_b = st.date_input("出生日期", min_value=min_date, max_value=max_date, value=None, key="db")
        time_b = st.time_input("出生时间 (不清楚填12:00)", value=time(12, 0), key="tb")
        city_name_b = st.selectbox("出生城市", list(CITY_DB.keys()), index=None, placeholder="可输入拼音搜索 (如 Wuhan)", key="cb")
        # 🔥 修改处：添加 B 的性别选择
        gender_b = st.selectbox("性别", ["male", "female"], format_func=lambda x: "男生" if x=="male" else "女生", key="gb")

    submitted = st.form_submit_button("🚀 开始深度鉴定")

if submitted:
    if not name_a or not name_b or not date_a or not date_b or not city_name_a or not city_name_b:
        st.error("❌ 信息不完整！请补全姓名、日期和城市。")
    elif not DEEPSEEK_API_KEY:
        st.error("🔒 缺少 API Key，无法启动 AI。")
    else:
        with st.spinner('🔭 正在连接宇宙能量场...时间可能会长一点'):
            try:
                loc_a = CITY_DB.get(city_name_a, CITY_DB["其他 (Default)"])
                loc_b = CITY_DB.get(city_name_b, CITY_DB["其他 (Default)"])

                sub_a = AstrologicalSubject(name_a, date_a.year, date_a.month, date_a.day, time_a.hour, time_a.minute, lng=loc_a['lng'], lat=loc_a['lat'], tz_str="Asia/Shanghai")
                sub_b = AstrologicalSubject(name_b, date_b.year, date_b.month, date_b.day, time_b.hour, time_b.minute, lng=loc_b['lng'], lat=loc_b['lat'], tz_str="Asia/Shanghai")

                synastry = SynastryAspects(sub_a, sub_b)
                raw_aspects = synastry.get_relevant_aspects()
                score, radar, filtered_aspects = calculate_commercial_score(raw_aspects)

                # 🔥 修改处：双向性别逻辑生成
                # 主角 A 分析
                moon_desc_a = get_sign_keyword('Moon', sub_a.moon['sign'])
                sun_desc_a = get_sign_keyword('Sun', sub_a.sun['sign'])
                if gender_a == 'male':
                    target_desc_a = get_sign_keyword('Venus', sub_a.venus['sign'])
                    desc_a_str = f"A({name_a},男): 外表{sun_desc_a}, 内心{moon_desc_a}, 喜欢{target_desc_a}型。"
                else:
                    target_desc_a = get_sign_keyword('Mars', sub_a.mars['sign'])
                    desc_a_str = f"A({name_a},女): 外表{sun_desc_a}, 内心{moon_desc_a}, 易被{target_desc_a}吸引。"

                # 主角 B 分析
                moon_desc_b = get_sign_keyword('Moon', sub_b.moon['sign'])
                sun_desc_b = get_sign_keyword('Sun', sub_b.sun['sign'])
                if gender_b == 'male':
                    target_desc_b = get_sign_keyword('Venus', sub_b.venus['sign'])
                    desc_b_str = f"B({name_b},男): 外表{sun_desc_b}, 内心{moon_desc_b}, 喜欢{target_desc_b}型。"
                else:
                    target_desc_b = get_sign_keyword('Mars', sub_b.mars['sign'])
                    desc_b_str = f"B({name_b},女): 外表{sun_desc_b}, 内心{moon_desc_b}, 易被{target_desc_b}吸引。"

                gender_prompt = f"{desc_a_str}\n{desc_b_str}"
                
                # 下面保持不变
                sorted_aspects = sorted(filtered_aspects, key=lambda x: 0 if x['aspect'] in ['conjunction', 'opposition'] else 1)
                top_aspects = []
                risk_flag = False
                for x in sorted_aspects[:4]:
                    guide = get_expert_guidance(x['p1_name'], x['p2_name'], x['aspect'])
                    desc = f"- {x['p1_name']} 与 {x['p2_name']} ({x['aspect']})"
                    if guide:
                        desc += f"\n  ({guide})"
                        if "高危" in guide or "风险" in guide: risk_flag = True
                    top_aspects.append(desc)

                tone = "虽然分数高但存在高危相位，请写成【宿命般的相爱相杀】" if (score > 85 and risk_flag) else "侧重描写甜蜜默契"

                prompt = f"""
                【角色】毒舌恋爱鉴定师。分析CP (匹配度{score}%)。基调：{tone}
                【输入】
                雷达图：激情{radar['P']}, 沟通{radar['C']}, 稳定{radar['S']}, 三观{radar['V']}
                主角揭秘：
                {gender_prompt}
                星象证据：{"; ".join(top_aspects)}
                【要求】(小红书风)
                1. 🏷️CP毒舌标签
                2. 💖缘分深度 (是宿命还是孽缘？)
                3. 💣潜伏危机 (重点！根据星象证据指出隐患)
                4. 💡拿捏指南 (结合双方喜好，给A出招搞定B)
                """
                
                report = call_ai_writer(prompt, DEEPSEEK_API_KEY)

                st.markdown(f"""
                <div class="score-box">
                    <h2 style='margin:0; opacity:0.8;'>💖 AI 测算契合度</h2>
                    <h1 style='font-size: 80px; margin:0; text-shadow: 2px 2px 4px rgba(0,0,0,0.2);'>{score}%</h1>
                </div>
                """, unsafe_allow_html=True)

                categories = ['激情 (P)', '沟通 (C)', '稳定 (S)', '三观 (V)']
                fig = go.Figure(data=go.Scatterpolar(
                    r=[radar['P'], radar['C'], radar['S'], radar['V']], 
                    theta=categories, fill='toself', marker=dict(color='#FF4B4B')
                ))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=250, margin=dict(t=20, b=20, l=40, r=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("### 📝 鉴定报告")
                st.info("⚠️ 结果仅供娱乐，但准得有点吓人...")
                st.write(report)
                st.balloons()

            except Exception as e:
                st.error(f"测算失败: {e}")