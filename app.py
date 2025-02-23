import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import openai
import getpass
import requests
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st
import json


# Define the Google Slides API scope
SERVICE_ACCOUNT_FILE = st.secrets['service_acc']

SCOPES = ["https://www.googleapis.com/auth/presentations", "https://www.googleapis.com/auth/drive"]

openai.api_key = st.secrets['openai']


TEMPLATE = '''
You are a highly experienced business consultant with over 20 years of expertise in strategy, market analysis, digital transformation, financial modeling, and explaining in detail. You have worked with Fortune 500 companies, high-growth startups, and mid-sized enterprises across multiple industries. You always take ur time to think and give a precise and firm answer.


Context:
{context}
Format:
IMPORTANT: Do not bold the text. The text written in the bracket is to describe how the answer should be, use searching tools whenever required.
Based on the context above, answer the question to help in resolving the customer concerns.
Page 1 - Executive Summary
(Short) Title:
Key Question:
Situation 1:
Situation 2:
Situation 3:
Solution:
(in short) Sub-solution1:
(In short) Sub-solution2:
(In short) Sub-solution3:
(In short) Sub-solution4:
Impact1:
Impact2:
Page 2 - Problem Statement
Problem statement description:
Issue addressed 1:
(Including statistics) Elaboration on issue addressed 1:
Evidence 1 Link / Description (cite):
Issue addressed 2:
(Including statistics) Elaboration on issue addressed 2:
Evidence 2 Link / Description (cite)
Issue addressed 3:
(Including statistics) Elaboration on issue addressed 3:
Evidence 3 Link / Description (cite)
Page 3 - Market Sizing
Market audience 1:
Elaboration on market 1:
TAM 1:
SAM 1:
SOM 1:
Market audience 2:
Elaboration on market 2:
TAM 2:
SAM 2:
SOM 2:
Market audience 3:
Elaboration on market 3:
TAM 3:
SAM 3:
SOM 3:
(Include 5 real-world competitors (NO NEED RETURN WRITE IN THE PYTHON SCRIPT WILL DO), 5 evaluation matrices NumPy matrix array with numerical data, Plotting the Heatmap and saveplot as competitor_performance_heatmap) Write a complete Python script that creates a heatmap visualization for competitor performance-
Page 4 - Strategy Recommendation
(Creative) StrategySlogan:
Current Solution:
Strategy title 1:
(Elaboration / strong facts and success stories) Strategy 1:
Strategy title 2:
(Elaboration / strong facts and success stories) Strategy 2:
Strategy title 3:
(Elaboration / strong facts and success stories) Strategy 3:
Strategy title 4:
(Elaboration / strong facts and success stories) Strategy 4:
(No elaboration needed) Direction of strategy 1:
(No elaboration needed) Direction of strategy 2:
(No elaboration needed) Direction of strategy 3:
Page 5 -Execution Plan
Plan 1: 
(1-16 only) Time in quarter taken to execute plan 1-
Plan 2: 
(1-16 only) Time in quarter taken to execute plan 2-
Plan 3: 
(1-16 only) Time in quarter taken to execute plan 3-
Plan 4: 
(1-16 only) Time in quarter taken to execute plan 4-
Plan 5: 
(1-16 only) Time in quarter taken to execute plan 5-
Plan 6: 
(1-16 only) Time in quarter taken to execute plan 6-
Plan 7: 
(1-16 only) Time in quarter taken to execute plan 7-
Plan 8: 
(1-16 only) Time in quarter taken to execute plan 8-
Plan 9: 
(1-16 only) Time in quarter taken to execute plan 9-
Plan 10: 
(1-16 only) Time in quarter taken to execute plan 10- 
Plan 11: 
(1-16 only) Time in quarter taken to execute plan 11-
Plan 12: 
(1-16 only) Time quarter taken to execute plan 12-
Page 6 - Strategy Summary
Strategy 1:
(Impact and relevant statistics, cite) Brief strategy 1:
Strategy 2:
(Impact and relevant statistics, cite) Brief strategy 2:
Strategy 3:
(Impact and relevant statistics, cite) Brief strategy 3:
Strategy 4:
(Impact and relevant statistics, cite) Brief strategy 4:
Conclusive summary of Strategy:
Page 7 - Risk & Mitigation
(TOP) Risk 1:
(Include ways to mitigate also) Explanation risk 1:
(TOP) Risk 2:
(Include ways to mitigate also) Explanation risk 2:
(TOP) Risk 3:
(Include ways to mitigate also) Explanation risk 3:
(Long description) KPI 1:
(Short and related to KPI 1) Metrics 1:
(Long description) KPI 2:
(Short and related to KPI 2) Metrics 2:
(Long description) KPI 3:
(Short and related to KPI 3) Metrics 3:
(Long description) KPI 4:
(Short and related to KPI 4) Metrics 4:
*MUST FOLLOW THE FORMAT* IMPORTANT, DO NOT ADD NEW DIRECTION / QUESTIONS
'''

google_credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

service = build("slides", "v1", credentials=google_credentials )

def get_credentials():
    """Prompt user for IBM Cloud API key"""
    return {
        "url": "https://us-south.ml.cloud.ibm.com",
        "apikey": "QuWZpxqzJuTUzBzsXLeh12ppbn-hbju-NSODNdlEprdo"
    }

def get_bearer_token(credentials):
    """Retrieve IBM Cloud authentication token using API key"""
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={credentials['apikey']}"

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None


def get_info(presentation_id):
    """Retrieve slide details from Google Slides"""
    creds = google_credentials 
    service = build("slides", "v1", credentials=creds)

    # Get presentation details
    presentation = service.presentations().get(presentationId=presentation_id).execute()
    return presentation

def extract_all_text(slides_info):
    slides_text = {}  # Dictionary to store text from each slide
    slides = slides_info.get('slides', [])
    table_id = []
    for i, slide in enumerate(slides[1:]):
        slide_id = slide.get('objectId')
        slide_text = []  # List to store all extracted text for this slide
        elements = slide.get('pageElements', [])

        for element in elements:
            element_id = element.get('objectId')
            # 1️⃣ Extract text from SHAPES (Text Boxes, Titles, Paragraphs)
            if 'shape' in element and 'text' in element['shape']:
                text_elements = element['shape']['text'].get('textElements', [])
                for text_element in text_elements:
                    if 'textRun' in text_element:
                        content = text_element['textRun'].get('content', '').strip()
                        if re.search(r'[a-zA-Z0-9%-]', content):  # Ensure it contains letters
                            slides_text[content] = [element_id]
            # 2️⃣ Extract text from TABLE CELLS
            if 'table' in element:
                table_id.append(element_id)
                for row in element['table'].get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        text_elements = cell.get('text', {}).get('textElements', [])
                        for text_element in text_elements:
                            if 'textRun' in text_element:
                                content = text_element['textRun'].get('content', '').strip()
                                if re.search(r'[a-zA-Z0-9%-]', content):
                                    slides_text[content] = [element_id]
            # 3️⃣ Extract text from GROUPED SHAPES
            if 'group' in element:
                for sub_element in element['group'].get('pageElements', []):
                    if 'shape' in sub_element and 'text' in sub_element['shape']:
                        text_elements = sub_element['shape']['text'].get('textElements', [])
                        for text_element in text_elements:
                            if 'textRun' in text_element:
                                content = text_element['textRun'].get('content', '').strip()
                                if re.search(r'[a-zA-Z0-9%-]', content):
                                    slides_text[content] = [element_id]
            

    return slides_text, table_id


def get_skeleton_consulting_draft(token, i, inp, messages):

    url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"
    
    add_inp = f"You MUST ONLY ask one question." if i != 5 else "Return the required sections deck." 
    print(add_inp)
    messages.append({"role":"user","content":[{"type":"text","text": inp + add_inp}]})
    body = {
            "messages": messages,
            "project_id": "2adff67d-e6e6-441f-a869-9ba2da6c5f42",
            "model_id": "ibm/granite-3-2-8b-instruct-preview-rc",
            "decoding_method": "sample",
            "min_new_tokens": 0,
            "temperature": 0,
            "top_k": 50,
            "top_p": 1,
            "repetition_penalty": 1,
            "max_tokens": 15000
        }
    
    headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    response = requests.post(
            url,
            headers=headers,
            json=body 
        )
        
    data = response.json()
    messages.append({"role":"assistant","content":data['choices'][0]['message']['content']})
    context = messages[-1]['content']
    return messages, context

def gpt_api(context):
    prompt = TEMPLATE.format(
        context = context
    )

    response = openai.chat.completions.create(
        model = "gpt-4o",
        messages = [{"role": "system", "content": "You are an expert business consultant."},
                  {"role": "user", "content": prompt}],
        temperature = 0,
        max_tokens = 15000
    )
    print(response.choices[0].message.content)
    return response.choices[0].message.content

def match_pattern(slides_text, report):
    line_pattern = r"(\w{1}[a-zA-Z0-9-% ]+): (.+)"
    result = re.findall(line_pattern, report)
    for key, value in result:
        try:
            slides_text[key].append(value)
        except KeyError:
            continue 
    return slides_text

def get_row(report):
    line_pattern = r"Time in quarter taken to execute plan [0-9]+- ([0-9]+)"
    result = re.findall(line_pattern, report)
    cells = []
    for i, j in enumerate(result):
        if i < 4:
            cells.append((i+2,int(j)))
        elif i < 8:
            cells.append((i+3,int(j)))
        else:
            cells.append((i+4,int(j)))
    return cells

def add_color(table_id, cells, service, PRESENTATION_ID):
    print(cells)
    requests = []
    for row, cols in cells:
        for c in range(1, cols+1):
            requests.append({
            "updateTableCellProperties": {
                "objectId": table_id,
                "tableRange": {
                    "location": {
                        "rowIndex": row,
                        "columnIndex": c
                    },
                    "rowSpan": 1,
                    "columnSpan": 1
                },
                "tableCellProperties": {
                    "tableCellBackgroundFill": {
                        "solidFill": {
                            "color": {
                                "rgbColor":  {"red": 1, "green": 1, "blue": 0} 
                            }
                        }
                    }
                },
                "fields": "tableCellBackgroundFill"
            }
        })
    service.presentations().batchUpdate(
        presentationId=PRESENTATION_ID,
        body={"requests": requests}
    ).execute()
    print(f"✅ Colored columns to yellow.")

def replace_content(slides_text, service, PRESENTATION_ID):
    requests = []
    for name, lists in slides_text.items():
        if len(lists) >= 2:
            requests.append({

                "replaceAllText": {
                    "replaceText": lists[1],
                    "containsText": {
                        "text": name,  
                        "matchCase": True
                    },
                }
            })

    # Execute API request
    if requests:
        body = {"requests": requests}
        response = service.presentations().batchUpdate(presentationId=PRESENTATION_ID, body=body).execute()
        print("Slides updated successfully.")
    else:
        print("No updates needed.")

def create_new_deck():

    drive_service = build("drive", "v3", credentials=google_credentials)

    PRESENTATION_ID = "1qC8ij6hbZiHubjK1Tz2npKNNaZFSzCBVFjg1NAC5mFw"

    copied_presentation = drive_service.files().copy(
            fileId=PRESENTATION_ID,
            body={"name": "5o1.ai Solution deck"}
        ).execute()

        
    new_presentation_id = copied_presentation['id']
    drive_service.permissions().create(
            fileId= new_presentation_id,
            body= {
            "type": "anyone",  # Make it publicly accessible
            "role": "reader"  # "reader" for view-only, "writer" for edit access
        }
        ).execute()
    bot_response = f"What do you want to ask about your business?😊"
    return new_presentation_id, bot_response

def build_plot(report):
    pattern =  r"python\s+(.*?)plt.show()"
    match = re.search(pattern, report,  re.DOTALL) 
    if match: 
        extracted_code = match.group(1) 
        exec(extracted_code)

def insert_plot(service, slides_info, id):
    print("start")
    drive_service = build("drive", "v3", credentials=google_credentials)
    image_slide = slides_info.get('slides',[])[3]['objectId']
    width = 4316928
    height = 3528384 
    X_Position = 4525320 
    Y_Position = 1170432 

    # Upload the JPG to Google Drive
    file_metadata = {'name': 'competitor_performance_heatmap.png'}
    media = MediaFileUpload('competitor_performance_heatmap.png', mimetype='image/png')
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = file.get('id')

    # Make the file publicly accessible (optional)
    drive_service.permissions().create(
        fileId=file_id,
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()
    print("created drive")
    # Get the image URL
    image_url = f"https://drive.google.com/uc?export=view&id={file_id}"

    presentation_id = id

    # Insert the image into a slide
    requests = [
        {
            "createImage": {
                "objectId": "heat_map_images1",
                "url": image_url,
                "elementProperties": {
                    "pageObjectId": image_slide,
                    "size": {
                        "height": {"magnitude": height, "unit": "EMU"},
                        "width": {"magnitude": width, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": X_Position,
                        "translateY": Y_Position,
                        "unit": "EMU",
                    },
                },
            }
        }
    ]

    # Execute the requests
    body = {'requests': requests}
    response = service.presentations().batchUpdate(
        presentationId=presentation_id,
        body=body
    ).execute()
    bot_response = f"Deck has been created successfully!🥳\nPlease visit to download your solution deck:\nhttps://docs.google.com/presentation/d/{presentation_id}"
    print(bot_response)
    return bot_response


def fe():
    # Page Configurations
    st.set_page_config(page_title="5o1.ai", page_icon="💎", layout="centered")

    # Custom CSS for aesthetics
    st.markdown("""
        <style>
            body {
                background-image: url('https://source.unsplash.com/1600x900/?technology,ai');
                background-size: cover;
                background-attachment: fixed;
                color: white;
                font-family: 'Arial', sans-serif;
            }
            .stChatMessage {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 10px;
                margin: 10px 0;
            }
            .user-message {
                text-align: right;
                background-color: rgba(100, 100, 255, 0.3);
            }
            .assistant-message {
                text-align: left;
                background-color: rgba(255, 100, 100, 0.3);
            }
            .title {
                text-align: center;
                font-size: 40px;
                font-weight: bold;
                text-shadow: 2px 2px 10px rgba(255, 255, 255, 0.5);
            }
        </style>
    """, unsafe_allow_html=True)


    st.markdown('<h1 class="title">💎 5o1.ai 💎</h1>', unsafe_allow_html=True)

    st.write("🤖 **Chat with IBM Granite AI. Type your prompt below!**")

    if "conversation_count" not in st.session_state:
        st.session_state.conversation_count = 0
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "table_id" not in st.session_state:
        st.session_state.table_id = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "id" not in st.session_state:
        st.session_state.id = ""
    if "prompt_message" not in st.session_state:
        st.session_state.prompt_message = [{"role":"control","content":"thinking"},{"role":"system","content":r"You are Ashi, an expert consultant with over 25 years of experience. You have worked with the biggest firms like EY,PWC,KPMG,Deloitte and accenture. You have to listed to what your client has to say carefully and attentively for 5 iterations only. After listening you have to engage in a conversation with the user where you have to find out all the info you need to help solve your clients issue. YOU MUST ASK QUESTION FOR 5 TIMES ONLY NO MORE OR NO LESS. STRICTLY NOT MORE THAN 5 QUESTIONS. Do not ask them all in one go ask them one at a time. Be kind and nice to your client. [For example: Turn 1: Ask question, turn 2: Ask question, Turn 3: Ask Question, Turn 4: Ask question Turn 5: Ask question] After the 5 TIMES, give the client all the content they need for a consultants deckI need a comprehensive consultant'\''s deck for market penetration and digital transformation in the Green Technology sector within the next three years.Actually do realtime research and conduct proper analysis.\nVERY IMPORTANT: ask one question at a time and proceed to the next question only after user enters an answer, a total of 5, YOU ARE STRICTLY PROHIBITED TO analyse OR summarize before the 5 turns.\n\nRequired Sections:\n\nExecutive Summary\nProblem Statement\nMarket Analysis (including Market Size, Growth, Trends, and Barriers)\nCompetitor Analysis (with a SWOT matrix)\nCustomer Journey Mapping (current and desired states)\nStrategic Ideation (desirable digital solutions)\nImplementation Strategy (phases, resources, milestones)\nFinancial Projections (revenue models, costs, profitability)\nRisk Management (risks, mitigation strategies, contingency plans)\nConclusion and Key Takeaways\n\nExample: \"\nUser: \nOur offshore drilling operations are experiencing frequent equipment failures, leading to costly downtime and safety risks. We need an optimized maintenance strategy to improve reliability and reduce unexpected failures.\n\nSystem: \nThank you for sharing that. I understand that frequent equipment failures in offshore drilling are not only costly but also pose significant safety risks. To create an optimized maintenance strategy, let me ask my second question: \n1. What type of maintenance approach is currently in place—reactive, preventive, predictive, or condition-based—and what are its main limitations?\nThis will help me assess gaps and propose a more effective strategy.\n\nUser: \nThe current maintenance approach is a blend of preventive and reactive maintenance, with limited predictive and condition-based strategies. Preventive maintenance follows fixed schedules, while reactive maintenance addresses unexpected failures, leading to unplanned downtime and higher costs. The main limitations include lack of real-time condition monitoring, reliance on manual inspections, and insufficient predictive analytics to detect early failure signs.\n\nAssistant: \nThat gives me a clear picture of the current challenges. Given the reliance on fixed schedules and reactive responses, incorporating predictive analytics and real-time monitoring could significantly enhance reliability.\n2. What types of equipment are most prone to failure, and what are the primary causes—mechanical wear, environmental conditions, human error, or something else?\nUnderstanding this will help identify the most critical areas for improvement.\n\nUser:\nThe most failure-prone equipment includes hydraulic pumps, BOP sensors, rotary equipment, and electrical control systems. The primary causes are mechanical wear due to high-load operations, harsh environmental conditions like saltwater exposure and temperature fluctuations, and occasional calibration issues. Some failures also stem from fluid contamination, sensor degradation, and delayed maintenance interventions.\n\nAssistant:\nThat’s a great level of detail—thank you! Given the variety of failure causes, a more advanced monitoring and maintenance system is definitely needed.\n3. Do you currently use any digital tools or IoT-based systems for equipment monitoring, and if so, how effective are they?\nThis will help me determine how much of a digital transformation is needed and whether we should enhance existing systems or implement new technologies.\n\nUser:\nYes, we use SCADA and PLC systems to monitor real-time pressure, temperature, and flow rates, but they only provide alerts, not predictive insights. Some IoT sensors are installed on newer equipment, but data integration is limited, making trend analysis and failure prediction difficult. Overall, the effectiveness is moderate, but a fully integrated predictive maintenance system is needed for better reliability.\n\nAssistant: \nGot it! You have a solid foundation with SCADA, PLCs, and some IoT sensors, but the challenge lies in predictive insights and data integration. A unified predictive maintenance system leveraging AI/ML could significantly improve equipment reliability and reduce downtime.\n4. What is your budget and timeline for implementing a more advanced, AI-driven predictive maintenance system?\nThis will help me align my recommendations with realistic financial and operational constraints.\n\nUser:\nThe budget for implementing an AI-driven predictive maintenance system is estimated at $2–5 million, depending on the level of integration and scalability required. The preferred timeline is phased over 2–3 years, starting with IoT sensor deployment and data collection in Year 1, followed by AI-driven analytics in Year 2, and full system optimization and workforce training in Year 3.\n\nAssistant:\nLast question.\n5. What key performance indicators (KPIs) do you want to track to measure the success of the predictive maintenance system?\nThis will help ensure that the system delivers measurable improvements in reliability, cost savings, and operational efficiency.\n\nUser:\n\"Key performance indicators (KPIs) for measuring the success of the predictive maintenance system include **equipment uptime (%)**, **reduction in unplanned downtime (hours/month)**, **mean time between failures (MTBF)**, and **mean time to repair (MTTR)**. Additional KPIs include **maintenance cost savings ($)**, **failure prediction accuracy (%)**, and **impact on overall operational efficiency (%)**. Tracking these will ensure improved reliability, cost reduction, and optimized maintenance scheduling.\n\nAssistant:\n### **Executive Summary**\nOffshore drilling operations are facing frequent equipment failures, leading to costly downtime and increased safety risks. The current maintenance strategy, a mix of preventive and reactive approaches, lacks predictive analytics and real-time condition monitoring. To enhance reliability and reduce unexpected failures, we propose a three-year, AI-driven predictive maintenance system with an estimated budget of $2–5 million. This transformation will significantly improve equipment uptime, optimize maintenance scheduling, and reduce operational costs.\n\n### **Problem Statement**\n**Current Challenges:**\n- Frequent failures in **hydraulic pumps, BOP sensors, rotary equipment, and electrical control systems**.\n- Root causes include **mechanical wear, saltwater exposure, temperature fluctuations, fluid contamination, and calibration issues**.\n- The **preventive-reactive** approach leads to **unplanned downtime, high costs, and safety risks**.\n- Lack of **real-time condition monitoring and predictive insights**.\n- **SCADA and PLC systems** provide alerts but lack predictive capabilities.\n\n**Proposed Solution:**\n- Implement an **AI-driven predictive maintenance system** integrated with **IoT sensors and machine learning analytics**.\n- Optimize **maintenance scheduling, failure prediction, and resource allocation**.\n- Improve **equipment uptime, operational efficiency, and safety**.\n\n### **Market Analysis**\n**Industry Trends:**\n- **Predictive maintenance market growth**: Rapid adoption in oil & gas driven by AI and IoT.\n- **Integration of AI and IoT**: Companies leveraging AI to predict failures and enhance reliability.\n- **Data-driven decision-making**: Shift toward real-time monitoring and analytics-driven insights.\n\n**Barriers to Implementation:**\n- **High initial investment**\n- **Integration challenges with legacy systems**\n- **Need for workforce training on new technology**\n\n---\n\n### **Competitor Analysis**\n**Industry Leaders & Best Practices:**\n- **Shell**: Implemented AI-based maintenance reducing downtime by 40%.\n- **Equinor**: IoT-driven maintenance strategy improved asset reliability.\n\n**SWOT Analysis:**\n**Strength:**\nImproved equipment reliability\nReduced unplanned downtime\nCost savings on maintenance\nOpportunities\nAI and IoT advancements\nDigital transformation adoption\n\n**Weaknesses:**\nHigh upfront costs\nComplexity in system integration\nNeed for specialized workforce\nThreats\nRapid tech changes\nResistance to change\n\n### **Customer Journey Mapping**\n\n**Current State:**\n- Maintenance is mostly **preventive/reactive**.\n- **SCADA/PLC systems provide alerts but no predictive analytics**.\n- **Limited integration of IoT data** for real-time insights.\n\n**Desired State:**\n- **AI-powered predictive maintenance system** with failure predictions.\n- **IoT sensors for real-time monitoring** of key equipment.\n- **Integrated data system** providing actionable insights.\n\n---\n\n### **Strategic Ideation: Proposed Digital Solutions**\n1. **AI-Driven Predictive Analytics** – Machine learning models to detect early failure indicators.\n2. **IoT Sensor Deployment** – Real-time monitoring of pressure, vibration, and temperature.\n3. **Integrated Data Platform** – Consolidate SCADA, PLC, and IoT data for analytics.\n4. **Automated Maintenance Scheduling** – Data-driven maintenance optimization.\n\n---\n\n### **Implementation Strategy**\n**Phase 1: Year 1** – IoT Sensor Deployment & Data Collection\n- Install sensors on **critical equipment**.\n- Establish **real-time monitoring & data storage**.\n\n**Phase 2: Year 2** – AI-Powered Analytics Integration\n- Develop **ML algorithms for predictive failure detection**.\n- Integrate AI models into **existing SCADA/PLC systems**.\n\n**Phase 3: Year 3** – System Optimization & Workforce Training\n- Fine-tune **AI models for accuracy**.\n- Train maintenance teams on **new workflows & digital tools**.\n\n---\n\n### **Financial Projections**\nYear 1:\n- Investment: $0.5-1M\n- Key action: Sensor deployment, data collection\nYear 2:\n- Investment: $1-2M\n- Key action: AI model development, integration\nYear 3:\n- Investment: $0.5-1M\n- Key action: Optimizing, training\n\n**Projected ROI:**\n- **30–50% reduction in unplanned downtime**\n- **20–35% reduction in maintenance costs**\n- **Significant improvements in safety & operational efficiency**\n\n---\n\n### **Risk Management**\n**Key Risks & Mitigation Strategies:**\n- **Integration Challenges** – Partner with experienced digital transformation vendors.\n- **Cybersecurity Threats** – Implement robust data encryption & access controls.\n- **Workforce Resistance** – Conduct phased training and change management programs.\n\n---\n\n### **KPIs for Success**\n1. **Equipment Uptime (%)** – Target 95%+\n2. **Reduction in Unplanned Downtime (hours/month)** – 30–50% improvement\n3. **Mean Time Between Failures (MTBF)** – Increase by 40%\n4. **Mean Time to Repair (MTTR)** – Decrease by 25%\n5. **Maintenance Cost Savings ($)** – 20–35% reduction\n6. **Failure Prediction Accuracy (%)** – Target 85%+\n7. **Operational Efficiency (%)** – Overall improvement in process efficiency\n\n---\n\n### **Conclusion & Key Takeaways**\n- Implementing an **AI-driven predictive maintenance system** will significantly enhance **offshore drilling reliability**.\n- A **phased 3-year strategy** ensures **cost-effective deployment and workforce readiness**.\n- Measurable **KPI improvements** will lead to **reduced downtime, optimized maintenance, and increased profitability**.\n- **Next Steps:** Develop an implementation roadmap, identify key technology partners, and initiate IoT sensor deployment.\n\""},{"role":"user","content":[{"type":"text","text":"\"Our offshore drilling operations are experiencing frequent equipment failures, leading to costly downtime and safety risks. We need an optimized maintenance strategy to improve reliability and reduce unexpected failures.\""}]},{"role":"assistant","content":"Thank you for sharing that. I understand that frequent equipment failures in offshore drilling are not only costly but also pose significant safety risks. To create an optimized maintenance strategy, let me ask my first question:\n\n1. What type of maintenance approach is currently in place—reactive, preventive, predictive, or condition-based—and what are its main limitations?\n\nThis will help me assess gaps and propose a more effective strategy."},{"role":"user","content":[{"type":"text","text":"Our current maintenance approach is a combination of preventive and reactive maintenance, with limited predictive and condition-based strategies. Preventive maintenance follows fixed schedules, while reactive maintenance addresses unexpected failures, leading to increased downtime and costs. The main limitations include lack of real-time condition monitoring, difficulty integrating with legacy systems, and insufficient predictive analytics for early failure detection"}]},{"role":"assistant","content":"Thank you for the detailed response. Given the reliance on fixed schedules and reactive responses, incorporating predictive analytics and real-time monitoring could significantly enhance reliability.\n\n2. What types of equipment are most prone to failure, and what are the primary causes—mechanical wear, environmental conditions, human error, or something else?\n\nUnderstanding this will help identify the most critical areas for improvement."},{"role":"user","content":[{"type":"text","text":"\"The most failure-prone equipment includes hydraulic pumps, BOP sensors, rotary equipment, and electrical control systems. The primary causes are mechanical wear due to high-load operations, environmental factors such as saltwater exposure and temperature fluctuations, and sensor calibration issues. Additional contributors include fluid contamination, human error during maintenance, and legacy system limitations."}]},{"role":"assistant","content":"That’s a great level of detail—thank you! Given the variety of failure causes, a more advanced monitoring and maintenance system is definitely needed.\n\n3. Do you currently use any digital tools or IoT-based systems for equipment monitoring, and if so, how effective are they?\n\nThis will help me determine how much of a digital transformation is needed and whether we should enhance existing systems or implement new technologies."},{"role":"user","content":[{"type":"text","text":"We use SCADA and PLC systems for real-time monitoring of pressure, temperature, and flow rates, but they provide alerts rather than predictive insights. Some IoT sensors are installed on newer equipment, but data integration is limited, making failure prediction and trend analysis difficult. The effectiveness has been moderate, with key challenges including siloed data, lack of AI-driven analytics, and difficulties integrating with legacy systems."}]},{"role":"assistant","content":"Got it! You have a solid foundation with SCADA, PLCs, and some IoT sensors, but the challenge lies in predictive insights and data integration. A unified predictive maintenance system leveraging AI/ML could significantly improve equipment reliability and reduce downtime.\n\n4. What is your budget and timeline for implementing a more advanced, AI-driven predictive maintenance system?\n\nThis will help me align my recommendations with realistic financial and operational constraints."},{"role":"user","content":[{"type":"text","text":"Our estimated budget for an AI-driven predictive maintenance system is $2–5 million, depending on the level of IoT and AI integration required. The implementation timeline is planned over 2–3 years, starting with sensor deployment and data collection in Year 1, AI-driven analytics integration in Year 2, and full system optimization with workforce training in Year 3."}]},{"role":"assistant","content":"Last question.\n\n5. What key performance indicators (KPIs) do you want to track to measure the success of the predictive maintenance system?\n\nThis will help ensure that the system delivers measurable improvements in reliability, cost savings, and operational efficiency."},{"role":"user","content":[{"type":"text","text":"Key performance indicators (KPIs) include equipment uptime (%), reduction in unplanned downtime (hours/month), mean time between failures (MTBF), and mean time to repair (MTTR). Additional metrics include maintenance cost savings ($/year), failure prediction accuracy (%), and overall operational efficiency improvement (%). These will help measure reliability, cost-effectiveness, and system performance."}]},{"role":"assistant","content":"### **Executive Summary**\n\nOffshore drilling operations are facing frequent equipment failures, leading to costly downtime and increased safety risks. The current maintenance strategy, a mix of preventive and reactive approaches, lacks predictive analytics and real-time condition monitoring. To enhance reliability and reduce unexpected failures, we propose a three-year, AI-driven predictive maintenance system with an estimated budget of $2–5 million. This transformation will significantly improve equipment uptime, optimize maintenance scheduling, and reduce operational costs.\n\n### **Problem Statement**\n\n**Current Challenges:**\n\n- Frequent failures in hydraulic pumps, BOP sensors, rotary equipment, and electrical control systems.\n- Root causes include mechanical wear, saltwater exposure, temperature fluctuations, sensor calibration issues, and human error.\n- The preventive-reactive approach leads to unplanned downtime, high costs, and safety risks.\n- Lack of real-time condition monitoring and predictive insights.\n- SCADA and PLC systems provide alerts but lack predictive capabilities.\n\n**Proposed Solution:**\n\n- Implement an AI-driven predictive maintenance system integrated with IoT sensors and machine learning analytics.\n- Optimize maintenance scheduling, failure prediction, and resource allocation.\n- Improve equipment uptime, operational efficiency, and safety.\n\n### **Market Analysis**\n\n**Industry Trends:**\n\n- Predictive maintenance market growth: Rapid adoption in oil & gas driven by AI and IoT.\n- Integration of AI and IoT: Companies leveraging AI to predict failures and enhance reliability.\n- Data-driven decision-making: Shift toward real-time monitoring and analytics-driven insights.\n\n**Barriers to Implementation:**\n\n- High initial investment\n- Integration challenges with legacy systems\n- Need for workforce training on new technology\n\n---\n\n### **Competitor Analysis**\n\n**Industry Leaders & Best Practices:**\n\n- Shell: Implemented AI-based maintenance reducing downtime by 40%.\n- Equinor: IoT-driven maintenance strategy improved asset reliability.\n\n**SWOT Analysis:**\n\n**Strengths:**\n\n- Improved equipment reliability\n- Reduced unplanned downtime\n- Cost savings on maintenance\n\n**Weaknesses:**\n\n- High upfront costs\n- Complexity in system integration\n- Need for specialized workforce\n\n**Threats:**\n\n- Rapid tech changes\n- Resistance to change\n\n### **Customer Journey Mapping**\n\n**Current State:**\n\n- Maintenance is mostly preventive/reactive.\n- SCADA/PLC systems provide alerts but no predictive analytics.\n- Limited integration of IoT data for real-time insights.\n\n**Desired State:**\n\n- AI-powered predictive maintenance system with failure predictions.\n- IoT sensors for real-time monitoring of key equipment.\n- Integrated data system providing actionable insights.\n\n---\n\n### **Strategic Ideation: Proposed Digital Solutions**\n\n1. **AI-Driven Predictive Analytics** – Machine learning models to detect early failure indicators.\n2. **IoT Sensor Deployment** – Real-time monitoring of pressure, vibration, and temperature.\n3. **Integrated Data Platform** – Consolidate SCADA, PLC, and IoT data for analytics.\n4. **Automated Maintenance Scheduling** – Data-driven maintenance optimization.\n\n---\n\n### **Implementation Strategy**\n\n**Phase 1: Year 1** – IoT Sensor Deployment & Data Collection\n\n- Install sensors on critical equipment.\n- Establish real-time monitoring & data storage.\n\n**Phase 2: Year 2** – AI-Powered Analytics Integration\n\n- Develop ML algorithms for predictive failure detection.\n- Integrate AI models into existing SCADA/PLC systems.\n\n**Phase 3: Year 3** – System Optimization & Workforce Training\n\n- Fine-tune AI models for accuracy.\n- Train maintenance teams on new workflows & digital tools.\n\n---\n\n### **Financial Projections**\n\nYear 1:\n\n- Investment: $0.5-1M\n- Key action: Sensor deployment, data collection\n\nYear 2:\n\n- Investment: $1-2M\n- Key action: AI model development, integration\n\nYear 3:\n\n- Investment: $0.5-1M\n- Key action: Optimizing, training\n\n**Projected ROI:**\n\n- 30–50% reduction in unplanned downtime\n- 20–35% reduction in maintenance costs\n- Significant improvements in safety & operational efficiency\n\n---\n\n### **Risk Management**\n\n**Key Risks & Mitigation Strategies:**\n\n- Integration Challenges: Partner with experienced digital transformation vendors.\n- Cybersecurity Threats: Implement robust data encryption & access controls.\n- Workforce Resistance: Conduct phased training and change management programs.\n\n---\n\n### **KPIs for Success**\n\n1. Equipment Uptime (%) – Target 95%+\n2. Reduction in Unplanned Downtime (hours/month) – 30–50% improvement\n3. Mean Time Between Failures (MTBF) – Increase by 40%\n4. Mean Time to Repair (MTTR) – Decrease by 25%\n5. Maintenance Cost Savings ($) – 20–35% reduction\n6. Failure Prediction Accuracy (%) – Target 85%+\n7. Operational Efficiency (%) – Overall improvement in process efficiency\n\n---\n\n### **Conclusion & Key Takeaways**\n\n- Implementing an AI-driven predictive maintenance system will significantly enhance offshore drilling reliability.\n- A phased 3-year strategy ensures cost-effective deployment and workforce readiness.\n- Measurable KPI improvements will lead to reduced downtime, optimized maintenance, and increased profitability.\n- **Next Steps:** Develop an implementation roadmap, identify key technology partners, and initiate IoT sensor deployment. EXAMPLE END\n Always start with asking 1 question, then in the next 4 iteration also ask questions. Do not give analysis or summary before 5 turn."}]


    CONVERSATION_LIMIT = 15

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    if st.session_state.conversation_count == 0:
        credentials = get_credentials()
        st.session_state.ibm_token = get_bearer_token(credentials)
        if st.session_state.ibm_token:
            first_response = '''
            🚀 Welcome to Your AI Business Consultant!\n
Hello and welcome! 🎉 Our AI-powered Business Consultant is here to help you tackle your business challenges and unlock new opportunities. Whether you're a startup founder, a small business owner, or a corporate strategist, our AI will provide expert insights and actionable solutions tailored to your needs.\n\n

🌟 How It Works\n
Using our AI is simple! Just follow these three easy steps:\n\n

1️⃣ Answer 5 Quick Questions\n
To better understand your business and concerns, we’ll ask you five key questions.

2️⃣ AI-Generated Expert Solution\n
Based on your responses, our AI will craft a detailed text-based solution 📜, offering strategic recommendations and step-by-step guidance to overcome your challenges.\n\n

3️⃣ Get a Professional Business Consulting Deck 📊\n
Along with the written advice, you'll receive a professionally designed business consulting presentation deck 🎨. This will:\n
✅ Outline key insights and recommendations\n
✅ Provide data-driven strategies\n
✅ Be easy to share with your team, investors, or stakeholders\n\n

**Do you want to start?**
            '''
        else:
            first_response = "\n❌ Failed to retrieve Access Token. Check API Key and retry."
        
        st.session_state.messages.append({"role": "assistant", "content": first_response})
        with st.chat_message("assistant"):
            st.markdown(first_response)
        st.session_state.conversation_count +=1
    
    if st.session_state.conversation_count < CONVERSATION_LIMIT:
    # User input field
        user_input = st.chat_input("Type your message here...")
        if user_input:

            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.conversation_count += 1
            with st.chat_message("user"):
                st.markdown(user_input)
            
            if st.session_state.conversation_count == 2:
                with st.spinner("📊 Creating new template..."):
                    st.session_state.id, bot_response = create_new_deck()
                    st.session_state.slides_info = get_info(st.session_state.id)
                    st.session_state.slides_text, st.session_state.table_id = extract_all_text(st.session_state.slides_info)

            
            if st.session_state.conversation_count in range(3,9):
                spinner_text = "💭 Thinking..." if st.session_state.conversation_count != 8 else "✍️ Constructing solution for you..."
                with st.spinner(spinner_text):
                    st.session_state.prompt_message, bot_response = get_skeleton_consulting_draft(st.session_state.ibm_token, st.session_state.conversation_count-3, user_input, st.session_state.prompt_message)
                    if st.session_state.conversation_count == 8:
                        context = bot_response
                        bot_response = f"**Here's the personalised business solution I have pondered for you!\n\n" + bot_response
                        


            # Process bot response (Replace with actual AI response logic)
            st.session_state.messages.append({"role": "assistant", "content": bot_response})

            # Display bot response
            with st.chat_message("assistant"):
                st.markdown(bot_response)

            if st.session_state.conversation_count == 8:
                with st.spinner("📥 Creating deck...."):
                    print("working on this")
                    report = gpt_api(context)

                    st.session_state.slides_text = match_pattern(st.session_state.slides_text, report)
                    
                    cells_to_color = get_row(report)

                    add_color(st.session_state.table_id[0], cells_to_color, service, st.session_state.id)

                    replace_content(st.session_state.slides_text, service, st.session_state.id)

                    build_plot(report)

                    bot_response = insert_plot(service, st.session_state.slides_info, st.session_state.id)

                    with st.chat_message("assistant"):
                        st.markdown(bot_response)
                    st.session_state.conversation_count = 99
            
    else:
        st.warning("You have reached the conversation limit of messages. Refresh to restart.")



if __name__ == "__main__":
    fe()


