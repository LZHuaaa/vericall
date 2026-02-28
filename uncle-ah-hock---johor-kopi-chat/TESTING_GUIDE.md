# 🧪 How to Test Uncle Ah Hock v2.0

Use this guide to verify that the advanced features (Bot Detection, Evidence, Auto-Aggression) are working correctly.

## 1. Test Bot Detection (Silent Call Defense)
*   **Goal:** Verify the app detects a caller waiting to clone your voice.
*   **Steps:**
    1.  Click the **Phone Icon** to connect.
    2.  **STAY COMPLETELY SILENT.** Do not speak into your microphone.
    3.  Wait for about 3-4 seconds.
*   **Expected Result:**
    *   A red **"BOT DETECTED"** warning should appear in the UI.
    *   The reason displayed should be: *"Caller silent for >3s. Possible Bot..."*
    *   Uncle Ah Hock should automatically say something like *"Hello? Who is this?"* to break the silence.

## 2. Test Real-Time Scam Recognition (Macau Scam)
*   **Goal:** Verify the system detects scam keywords and the meter rises.
*   **Steps:**
    1.  Connect to the call.
    2.  Roleplay as a scammer. Say clearly:
        > "Hello, I am calling from the **Police**. You have an outstanding **arrest warrant**."
    3.  Watch the UI.
*   **Expected Result:**
    *   **Pattern Alert:** An orange "PATTERN MATCHED" banner should appear showing "Macau Scam".
    *   **Threat Meter:** The threat level bar should jump significantly (e.g., from 0% to 50%+).
    *   **AI Reaction:** Uncle Ah Hock should react defensively (e.g., *"Police? Which station? I call my lawyer now!"*).

## 3. Test Auto-Aggression
*   **Goal:** Verify the AI counter-attacks without you clicking buttons.
*   **Steps:**
    1.  Connect to the call.
    2.  Say with urgency:
        > "You must **transfer** the money **immediately** or you will be **arrested**!"
*   **Expected Result:**
    *   The system detects "Critical" urgency.
    *   You might see a log entry: `System: [INSTRUCTION: ... ATTACK THEM ...]`.
    *   Uncle Ah Hock should get angry/aggressive immediately.

## 4. Test Evidence Collection & PDRM Report
*   **Goal:** Generate a police report after the call.
*   **Steps:**
    1.  Have a short conversation (10-20 seconds) mentioning "Money" or "Bank".
    2.  Click the **Red Phone Icon** (Disconnect).
    3.  Look at the top right header. A **Red File Icon** should appear/pulse.
    4.  Click the **Red File Icon**.
*   **Expected Result:**
    *   A modal opens titled **"PDRM SCAM REPORT"**.
    *   It shows the **Case ID**, **Duration**, and **Scam Type**.
    *   It lists the **Keywords Found** (e.g., "Bank", "Transfer").
    *   It shows the **Full Transcript** of your conversation.

## 5. Test Director Mode
*   **Goal:** Manually control the AI.
*   **Steps:**
    1.  Connect to the call.
    2.  Click the **"💔 FAKE ATTACK"** button.
*   **Expected Result:**
    *   Uncle Ah Hock should immediately stop his current sentence and pretend to have health issues (e.g., *"Argh... my heart... wait..."*).

## 6. Test Text Analysis Mode
*   **Goal:** Use Gemini 3 Pro reasoning.
*   **Steps:**
    1.  Switch the toggle from "Voice Mode" to **"Text Analysis"**.
    2.  Type: *"Is 03-2616 8888 a scam number?"*
    3.  Click Send.
*   **Expected Result:**
    *   The system uses the `googleSearch` tool to look it up.
    *   It should reply with facts (e.g., identifying it as a legit bank number or a reported scam number based on real search results).
