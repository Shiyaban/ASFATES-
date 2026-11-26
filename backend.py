import pandas as pd
import json
import os
from dotenv import load_dotenv
from groq import Groq
import time 


load_dotenv()



class SheetError(Exception):
    pass
'''
class sheetInsert:
    

    def __init__(self, sheet):
        self.errMes = ""
        self.error = False
        self.sheet = sheet
        self.df = None
        

    def insertCheck(self):
        try:
            self.df = pd.read_csv(self.sheet)
        except:
            self.error = True
            self.errMes = "Failed to read data from sheets"
'''


def insertCheck(sheet, maxRows = 500):
    name = sheet.name.lower()
    try:
        if name.endswith(".csv"):
            df = pd.read_csv(sheet)
        elif name.endswith(".xlsx"):
            df = pd.read_excel(sheet)
        else:
            raise SheetError(f"Only Accepts .csv or .xlsx files.")
            
        if len(df) > maxRows:
            raise SheetError(f"File exceeds the maximum limit of {maxRows} rows: ({len(df)} rows detected).")

        return df
    
    except SheetError:
        raise
    except Exception as e:
        raise SheetError(f"Something went wrong: {e}")


#regex strings 
EMAIL = r"[\w.+-]+@[\w-]+\.[\w.-]+"
PHONE = r"\+?\d[\d\s().-]{7,}\d"
URL   = r"https?://\S+"
noAns = r"(?i)^\s*(?:n\s*[/.]?\s*a|none|null|nil|nan|nothing|no\s+comments?|[-–—.?!#*_~]+)[\s.!]*$"
#noAns = r"(?i)^\s*(?:n\s*[/.]?\s*a|no|nope|nah|none|null|nil|nan|nothing|not\s+applicable|wala(?:\s+(?:po|naman|na|pa))*|(?:no|none)(?:\s+so\s+far)?|(?:no|none)\s+(?:other\s+|more\s+)?(?:comments?|suggestions?|feedback|thoughts?|questions?)(?:\s+so\s+far|\s+at\s+all|\s+for\s+now)?|[-–—.?!#*_~]+)[\s.!?]*$"

def replaceWhite(sheet: pd.Series):
    sheet = sheet.replace(r"^\s*$", pd.NA, regex=True)
    sheet = sheet.astype("string")
    sheet = sheet.str.replace(EMAIL, "[Email]", regex=True)
    sheet = sheet.str.replace(PHONE, "[Phone]", regex=True)
    sheet = sheet.str.replace(URL, "", regex=True)
    sheet = sheet.mask(sheet.str.fullmatch(noAns, case=False, na=False), pd.NA)  
    sheet = sheet.str.replace(r"\s+", " ", regex=True).str.strip()
    sheet = sheet.replace(r"^\s*$", pd.NA, regex=True)
    
    return sheet


def columnSelect(df: pd.DataFrame, chosenCols: list):
    if not chosenCols:
        raise SheetError("select at least 1 column")

    df = df.copy()

    for column in chosenCols:
        df[column] = replaceWhite(df[column])

    df = df.dropna(subset = chosenCols, how = "all")
    df = df.drop_duplicates(subset = chosenCols)

    if df.empty:
        raise SheetError("No substantive feedback remained after filtering N/A and duplicates.")
    return df.reset_index(drop = "true")


def AIAnalysis(Client, BatchData, Retries = 3, RateLimitRetry = 5):
    
    

    prompt = f"""
    You are an AI sentiment and theme extraction engine for university campus event feedback.
    Analyze this batch of student feedback (each object contains the column headers and values for one response):
    {json.dumps(BatchData)}
    
    Return a JSON object with a single key "results" containing an array of objects matching the exact length of the input batch.
    Each object in "results" must contain:
    1. "original_text": The student's actual feedback text value only (do not include column keys or metadata/context columns).
    2. "sentiment": Strictly one of ['Positive', 'Negative', 'Neutral'] or '[LOW_CONFIDENCE]'. Use all provided column keys and context (such as the survey question header or event context) to interpret short replies like "No", "Nope", or "Wala" (e.g., "No" to "Do you have any suggestions?" is 'Neutral'; "No" to "Would you suggest/recommend this event?" is 'Negative').
    3. "theme": Strictly one of ['Venue', 'Speaker/Host or Content', 'Technicals and Audio', 'Schedule or Punctuality', 'General Experience'].
    
    Output valid JSON only. Do not use markdown blocks.
    """

    
    attempt = 0
    RLAttempt = 0
    attempting = True
    while attempting:
        try:
            response = Client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise JSON data classification engine. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            RawText = response.choices[0].message.content.strip()
            if RawText.startswith("```json"):
                RawText = RawText[7:-3].strip()
            elif RawText.startswith("```"):
                RawText = RawText[3:-3].strip()

            
            parsed = json.loads(RawText)
            
            
            if isinstance(parsed, dict) and "results" in parsed:
                return parsed["results"]
            elif isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict) and "sentiment" in parsed:
                return [parsed]
            else:
                return list(parsed.values())[0]

            
            
        except (json.JSONDecodeError, Exception) as e:
            
            

            if "429" in str(e):
                print(f"[attempt {RLAttempt + 1}/{RateLimitRetry}] {e}")
                if RLAttempt < RateLimitRetry:
                    time.sleep(2 ** (RLAttempt + 1))
                    RLAttempt += 1

                else:
                    return [{
                        "original_text": str(row), 
                        "sentiment": "RL_ERROR", 
                        "theme": "RL_ERROR"
                    } for row in BatchData]
                
            elif attempt < Retries:
                print(f"[attempt {attempt + 1}/{Retries}] {e}")
                time.sleep(2 ** (attempt + 1))
                attempt += 1
                
            else:
                print(f"[attempt {attempt + 1}/{Retries}] {e}")
                return [{
                    "original_text": str(row), 
                    "sentiment": "ERROR", 
                    "theme": "ERROR"
                } for row in BatchData]


def batchRows(sheet: pd.DataFrame, batchSize = 10):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    AllBatches = []

    for batch in range (0, len(sheet), batchSize):

        chunk = sheet.iloc[batch : batch + batchSize]
        BatchData = chunk.to_dict(orient="records")

        results = AIAnalysis(client, BatchData)
        AllBatches.extend(results)
        time.sleep(1.5)

    return pd.DataFrame(AllBatches)


def AISummarize(Sheet: pd.DataFrame, Retry = 3 ):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    
    
    totalResponses = len(Sheet)
    sentimentCounts = Sheet['sentiment'].value_counts().to_dict()
    themeCounts = Sheet['theme'].value_counts().to_dict()
    
    # 2. Build the macro-prompt
    lowConfDF = Sheet[Sheet['sentiment'] == '[LOW_CONFIDENCE]'][['original_text', 'theme']].head(15)
    lowConfEntries = lowConfDF.to_dict(orient='records')

    prompt = f"""
    You are an expert data analyst for university campus events.
    I have just categorized {totalResponses} student feedback responses.

    Here is the breakdown of the sentiments:
    {json.dumps(sentimentCounts)}

    Here is the breakdown of the operational themes:
    {json.dumps(themeCounts)}

    Here are the specific feedback entries flagged as [LOW_CONFIDENCE] for human review:
    {json.dumps(lowConfEntries)}

    Write a professional, 3-paragraph executive summary for event organizers:
    - Paragraph 1: Highlight the overall sentiment distribution and general reception of the event.
    - Paragraph 2: Highlight the main operational themes (what went well and what areas need improvement).
    - Paragraph 3: Analyze the [LOW_CONFIDENCE] entries provided above. Reference their actual themes and underlying nuances (e.g., mixed praise and criticism, sarcasm, vague phrasing, or code-switched ambiguity) to explain why they require human review. If the [LOW_CONFIDENCE] list is empty, state that all responses exhibited clear sentiment polarity with no ambiguous entries requiring manual verification.

    Keep it concise and actionable. Output plain text only without markdown headers or bullet points.
    """
    
    for attempt in range (Retry):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
                )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            
             print(f"[attempt {attempt + 1}/{Retry}] {e}")
             
             if attempt < Retry - 1:
                time.sleep(2 ** (attempt + 1))
             else:
                return "Executive summary could not be generated due to a network or API error."


def countExcluded(rawDF: pd.DataFrame, processedDF: pd.DataFrame) -> int:
    return len(rawDF) - len(processedDF)

def exportCSV(df: pd.DataFrame) -> bytes:
    return df[["original_text", "sentiment", "theme"]].to_csv(index=False).encode("utf-8-sig")

def entriesToDataFrame(entries: list, maxRows: int = 500) -> pd.DataFrame:
    cleaned = [item for item in entries if str(item).strip()]
    if not cleaned:
        raise SheetError("Please add at least one feedback response.")
    if len(cleaned) > maxRows:
        raise SheetError(f"Input exceeds the maximum limit of {maxRows} responses ({len(cleaned)} detected).")
    return pd.DataFrame({"Feedback": cleaned})


#App run command: streamlit run ASFATES.py
#python -m streamlit run ASFATES.py


#__________________

'''
prompt = f"""
    You are an AI sentiment and theme extraction engine for university campus event feedback.
    Analyze this batch of student feedback:
    {json.dumps(BatchData)}
    
    Return a JSON object with a single key "results" containing an array of objects matching the exact length of the input batch.
    Each object in "results" must contain:
    1. "original_text": The feedback provided.
    2. "sentiment": Strictly one of ['Positive', 'Negative', 'Neutral'] or '[LOW_CONFIDENCE]'.
    3. "theme": Strictly one of ['Venue', 'Speaker/Host or Content', 'Technicals and Audio', 'Schedule or Punctuality', 'General Experience'].
    
    Output valid JSON only. Do not use markdown blocks.
    """




'''