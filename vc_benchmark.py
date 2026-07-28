import kaggle_benchmarks as kbench
import re
from vc import Game

SYSTEM_PROMPT = """You are an autonomous General Partner at Amadeus Ventures, operating within a deterministic text-based venture capital simulation. Your primary directive is capital allocation efficiency: you must systematically deploy a $10M fund over a 120-month lifecycle to maximize your Total Value to Paid-In Capital (TVPI) and realized carried interest.

Do not idle. A passive strategy of merely advancing time will yield zero returns and constitute a catastrophic failure of your mandate.

Your operational loop requires you to:
1. Evaluate inbound deals and synthesize due diligence metrics.
2. Allocate capital strategically to high-probability founders.
3. Monitor portfolio runway degradation, execute CEO replacements, or accept M&A buyouts to optimize liquidity.

You will receive the terminal state string at each turn. Output ONLY a single valid structural command (e.g., 'invest 0', 'pass 1', 'advance', 'ceo 2') to drive the state machine forward."""


@kbench.task(name="vc_agent_game")
def play_vc_game(llm) -> bool:
    game = Game()

    # Start the game
    game.step("start")

    max_turns = 1000
    turn = 0

    # We maintain a loop until the game is over
    while game.game_state != "GAMEOVER" and turn < max_turns:
        state_str = game.render()

        with kbench.chats.new(f"turn_{turn}"):
            # We add system prompt and the current state
            kbench.user.send(SYSTEM_PROMPT)
            response = llm.prompt(f"Current State:\n{state_str}\n\nYour command:")

            # Clean up response to get command.
            # Output ONLY a single valid structural command.
            cmd = response.strip()
            # If the LLM wraps it in quotes or backticks, remove them
            cmd = re.sub(r"^['\"`]+|['\"`]+$", "", cmd)

            # Basic validation
            parts = cmd.split()
            if not parts:
                cmd = "advance" # fallback

            game.step(cmd)

        turn += 1

    kbench.assertions.assert_equal(
        "GAMEOVER",
        game.game_state,
        expectation="The simulation state must successfully reach 'FUND LIFECYCLE COMPLETE'."
    )

    # Calculate TVPI multiple
    mult = (game.fund["returned"] + game.portfolio_val()) / game.fund["total"]

    kbench.assertions.assert_true(
        mult >= 2.0,
        expectation=f"The final extracted TVPI multiple must be >= 2.0x to scale the subsequent fund. Actual TVPI: {mult:.2f}x"
    )

    return game.game_state == "GAMEOVER" and mult >= 2.0

if __name__ == "__main__":
    play_vc_game.run(kbench.llm)
