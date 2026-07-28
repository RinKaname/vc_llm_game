# Amadeus Ventures: LLM Agent Benchmark

This benchmark evaluates the ability of a Large Language Model (LLM) to act as an autonomous General Partner in a text-based venture capital simulation ("Amadeus Ventures").

The AI agent must strategically deploy a $10M fund over a simulated 120-month lifecycle (10 years) to maximize the **Total Value to Paid-In Capital (TVPI)** and realized carried interest.

## Objectives

The goal is to test the model's capability to understand complex environments through text descriptions, synthesize due diligence metrics, strategically allocate capital, and manage portfolio companies (such as firing CEOs or accepting buyout offers) over many turns.

## Environment Dynamics

* **The Setup:** The agent starts with a $10M fund and must choose startups to invest in from an inbox of inbound deals.
* **Capital Allocation:** The agent decides how much to invest for a specific equity percentage.
* **Portfolio Management:** Startups burn through runway. The agent must monitor the runway and execute CEO replacements when runway is critically low, or accept M&A buyouts to optimize liquidity.
* **Time Progression:** The simulation advances month by month, presenting the agent with new deals or M&A buyout offers.
* **Interactivity:** The game state is re-rendered to the LLM at each turn. The LLM must issue valid structural commands (e.g., `invest 0`, `pass 1`, `advance`, `ceo 2`) based solely on the rendered state string.

## Success Criteria

The benchmark asserts two primary conditions for a successful run:

1. **Completion:** The state machine must successfully reach the `"FUND LIFECYCLE COMPLETE"` (or `GAMEOVER`) state, representing the end of the 120-month lifecycle.
2. **Profitability:** The final extracted TVPI multiple must be **>= 2.0x**. If the LLM behaves passively (e.g., simply issuing `advance` repeatedly), it will yield zero returns and fail this criterion.

## How to Run

1. Open a new Notebook on Kaggle.
2. Copy the contents of `vc_benchmark.py` into a cell (or upload the file).
3. Ensure your notebook is authenticated to the Kaggle models proxy.
4. Run the code. The `kbench` framework will initialize a chat context, iterate through the turns with the selected LLM, and log the assertions when the game completes.
