import streamlit as st
import plotly.express as px
import pandas as pd
import backend
import pdfExport



st.set_page_config(
    page_title="ASFATES - Student Feedback Analysis",
    page_icon="📊",
    layout="wide"
)
st.title("ASFATES: Dashboard")


st.write(f"""

Sentiments and Feedback Analysis for Events.  

To use:

Select Columns that have the sentiments/feedback of the Spreadsheet.

Ensure that the chosen column is only feedbacks, refrain from selecting other columns that is not feedback related as it wastes tokens.
""")


if "frame" not in st.session_state:
    st.session_state.frame = "upload"

currStatus = st.session_state.get("status", "idle")
isRunning = (currStatus == "running")

fBtn1, fBtn2, _ = st.columns([1.3, 1.3, 4.4])
with fBtn1:
    if st.button("Upload Spreadsheet", type="primary" if st.session_state.frame == "upload" else "secondary", disabled=isRunning, use_container_width=True):
        st.session_state.frame = "upload"
        st.session_state.current_file_id = None
        st.session_state.df = None
        st.session_state.batches = None
        st.session_state.summary = None
        st.session_state.status = "idle"
        st.rerun()
with fBtn2:
    if st.button("Direct Live Insertion", type="primary" if st.session_state.frame == "live" else "secondary", disabled=isRunning, use_container_width=True):
        st.session_state.frame = "live"
        st.session_state.current_file_id = None
        st.session_state.df = None
        st.session_state.batches = None
        st.session_state.summary = None
        st.session_state.status = "idle"
        st.rerun()

if st.session_state.frame == "upload":
    userSheet = st.file_uploader("Upload Files to Analyze Here: ", type=["csv", "xlsx"], disabled=isRunning)
    hasInput = userSheet is not None
else:
    userSheet = None
    if "liveEntries" not in st.session_state:
        st.session_state.liveEntries = []

    def addSingleEntry():
        text = st.session_state.get("live_box", "").strip()
        if text:
            st.session_state.liveEntries.append(text)
            st.session_state.live_box = ""
        

    def addLineByLine():
        lines = [line.strip() for line in st.session_state.get("live_box", "").splitlines() if line.strip()]
        if lines:
            st.session_state.liveEntries.extend(lines)
            st.session_state.live_box = ""

    st.text_area(
        "Enter student feedback:",
        height=150,
        key="live_box",
        placeholder="Paste a multi-paragraph response and click 'Add as Single Response', or paste multiple lines and click 'Add Line-by-Line'...",
        disabled=isRunning,
    )

    addCol1, addCol2, addCol3, _ = st.columns([1.4, 1.3, 0.9, 3.4])
    with addCol1:
        st.button("Add as Single Response", on_click=addSingleEntry, disabled=isRunning, use_container_width=True)
    with addCol2:
        st.button("Add Line-by-Line", on_click=addLineByLine, disabled=isRunning, use_container_width=True)
    with addCol3:
        if st.button("Clear List", disabled=(not st.session_state.liveEntries or isRunning), use_container_width=True):
            st.session_state.liveEntries = []
            st.session_state.batches = None
            st.session_state.summary = None
            st.session_state.status = "idle"
            st.rerun()

    if st.session_state.liveEntries:
        st.caption(f"Queued responses: {len(st.session_state.liveEntries)} / 500")
        st.dataframe(
            pd.DataFrame({"Queued Feedback": st.session_state.liveEntries}),
            use_container_width=True,
            hide_index=True,
        )

    hasInput = bool(st.session_state.liveEntries)


if hasInput:
    
    try:

        if st.session_state.frame == "upload":
            if st.session_state.get("current_file_id") != userSheet.file_id:
                st.session_state.current_file_id = userSheet.file_id
                st.session_state.df = backend.insertCheck(userSheet)
                st.session_state.results = None
                st.session_state.summary = None
                st.session_state.batches = None
                st.session_state.status = "idle"
                st.session_state.excludedCount = 0

            if st.session_state.get("df") is None:
                st.session_state.df = backend.insertCheck(userSheet)

            reqColumns = st.multiselect("Select columns", st.session_state.df.columns, key=f"cols_{userSheet.file_id}", disabled=isRunning)
        else:
            reqColumns = ["Feedback"] if st.session_state.liveEntries else []
        
        #Analyssis
        ctxCol1, ctxCol2 = st.columns(2)
        defaultQuestion = ", ".join(reqColumns) if reqColumns else ""
        
        
        with ctxCol1:
            eventContext = st.text_input(
                "Event Name / Context (Optional)",
                placeholder="e.g., CCIS Tech Seminar 2026 - Cybersecurity Workshop",
                disabled=isRunning
            )
        with ctxCol2:
            questionContext = st.text_input(
                "Survey Question Asked (Can be replaced for context)",
                placeholder=defaultQuestion,
                key=f"q_ctx_{defaultQuestion}",
                disabled=isRunning
            )
        
        
        btnCol1, btnCol2, _ = st.columns([1, 1, 5])
        with btnCol1:
            if st.button("Analyze", disabled=(not reqColumns or isRunning), use_container_width=True):
                if st.session_state.frame == "live":
                    st.session_state.df = backend.entriesToDataFrame(st.session_state.liveEntries)
                st.session_state.status = "running"
                st.rerun()

        with btnCol2:
            if isRunning:
                if st.button("Cancel", type="primary", use_container_width=True):
                    st.session_state.status = "cancelled"
                    st.rerun()

        if currStatus == "cancelled":
            st.warning("Analysis cancelled.")
        elif currStatus == "done":
            st.success("Analysis Complete.")

        if isRunning:
            with st.spinner("Analyzing..."):
                processedDF = backend.columnSelect(st.session_state.df, reqColumns)
                selectedColumns = processedDF[reqColumns].copy()

                if eventContext.strip():
                    selectedColumns["Event Context"] = eventContext.strip()
                
                finalQuestion = questionContext.strip() or defaultQuestion
                if finalQuestion:
                    selectedColumns["Survey Question"] = finalQuestion

                st.session_state.excludedCount = backend.countExcluded(st.session_state.df, processedDF)
                                
                st.write(f"Number of rows masked/deleted via cleaning: {st.session_state.excludedCount}")
                
                st.dataframe(selectedColumns[reqColumns])
                
               
                batches = backend.batchRows(selectedColumns)
                st.session_state.batches = batches

                summary = backend.AISummarize(batches)
                st.session_state.summary = summary

                st.session_state.status = "done"

                st.rerun()


                
                

        if st.session_state.get("batches") is not None and not isRunning:
            ResultBatch = st.session_state.batches
            st.divider()
            st.title("Summary")
            st.info(st.session_state.summary)

            st.divider()
            st.title("Reports")

            excludedCount = st.session_state.get("excludedCount", 0)
            reviewCount = int(ResultBatch["sentiment"].isin(["[LOW_CONFIDENCE]", "ERROR", "RL_ERROR"]).sum())

            
            column1, column2 = st.columns(2)

            with column1:
                st.write("Sentiments Result")
                SentimentCounts = ResultBatch["sentiment"].value_counts().reset_index()
                SentimentCounts.columns = ["Sentiment", "Count"]
                FigureSentiment = px.pie(SentimentCounts, names='Sentiment', values='Count', hole=0.4,
                                  color='Sentiment', color_discrete_map={
                                      'Positive': '#00cc96', 
                                      'Neutral': '#636efa', 
                                      'Negative': '#ef553b',
                                      '[LOW_CONFIDENCE]': '#ffa15a'
                                  })

                st.plotly_chart(FigureSentiment, use_container_width=True)
            
            with column2:
                st.write("Themes Result")
                ThemeCounts = ResultBatch['theme'].value_counts().reset_index()
                ThemeCounts.columns = ["Theme", "Count"]

                FigureTheme = px.bar(ThemeCounts, x='Theme', y='Count', color='Theme')
                st.plotly_chart(FigureTheme, use_container_width=True)

            st.divider()
            st.title("Spreadsheet Results")

            m1, m2, m3 = st.columns(3)
            m1.metric("Substantive Responses Analyzed", len(ResultBatch))
            m2.metric("Excluded (N/A & Duplicates)", excludedCount)
            m3.metric("Flagged for Human Review", reviewCount)
            
            fCol1, fCol2 = st.columns(2)
            with fCol1:
                selectedSentiments = st.multiselect(
                    "Filter by Sentiment",
                    options=ResultBatch["sentiment"].unique().tolist(),
                    default=ResultBatch["sentiment"].unique().tolist(),
                )
            with fCol2:
                selectedThemes = st.multiselect(
                    "Filter by Theme",
                    options=ResultBatch["theme"].unique().tolist(),
                    default=ResultBatch["theme"].unique().tolist(),
                )

            filteredResults = ResultBatch[
                ResultBatch["sentiment"].isin(selectedSentiments)
                & ResultBatch["theme"].isin(selectedThemes)
            ]

            st.dataframe(
                filteredResults[["original_text", "sentiment", "theme"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "original_text": st.column_config.TextColumn("Feedback", width="large"),
                    "sentiment": st.column_config.TextColumn("Sentiment", width="small"),
                    "theme": st.column_config.TextColumn("Theme", width="medium"),
                },
            )

            #ngl BEYOND THIS POINT IDK how this works...

            filePrefix = (
                "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in eventContext.strip())
                or "ASFATES"
            )
            summaryOutput = st.session_state.get("summary", "")

            dlCol1, dlCol2 = st.columns(2)
            with dlCol1:
                st.download_button(
                    label="Download Classified Feedback (.csv)",
                    data=backend.exportCSV(ResultBatch),
                    file_name=f"{filePrefix}_Classified_Feedback.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with dlCol2:
                st.download_button(
                    label="Download Report Summary (.pdf)",
                    data=pdfExport.exportPDF(
                        df=ResultBatch,
                        summaryText=summaryOutput,
                        eventContext=eventContext,
                        questionContext=finalQuestion if "finalQuestion" in locals() else defaultQuestion,
                        excludedCount=excludedCount,
                    ),
                    file_name=f"{filePrefix}_Executive_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            

        
    except backend.SheetError as e:
        st.session_state.status = "idle"
        st.error(f"Something went wrong {e}")

else:
    st.session_state.current_file_id = None
    st.session_state.df = None
    st.session_state.results = None
    st.session_state.summary = None
    st.session_state.status = "idle"
    st.session_state.excludedCount = 0


#App run command: streamlit run ASFATES.py
#Unblocked run: python -m streamlit run ASFATES.py


oldStuff='''

if userSheet is not None:
    
    try:

        if st.session_state.get("current_file_id") != userSheet.file_id:
            st.session_state.current_file_id = userSheet.file_id
            st.session_state.df = backend.insertCheck(userSheet)
            st.session_state.results = None
            st.session_state.summary = None
            st.session_state.batches = None
            st.session_state.status = "idle"
            st.session_state.excludedCount = 0


        currStatus = st.session_state.get("status", "idle")
        isRunning = (currStatus == "running")
        
        
        if "df" not in st.session_state:
            st.session_state.df = backend.insertCheck(userSheet)
        
        reqColumns = st.multiselect("Select columns", st.session_state.df.columns, key=f"cols_{userSheet.file_id}", disabled = isRunning)
        

'''