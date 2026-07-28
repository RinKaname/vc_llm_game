import random
import sys
import re
import kaggle_benchmarks as kbench

# ---------- Constants ----------
NAMES_FIRST = ["Aero", "Cloud", "Cyber", "Data", "Deep", "Neuro", "Nova",
               "Omni", "Quantum", "Syn", "Tech", "Zen"]
NAMES_LAST  = ["AI", "Block", "Base", "Box", "Chain", "Coin", "ify",
               "Hub", "Link", "Net", "Node", "Sys"]
SECTORS = ["SAAS", "FINTECH", "CRYPTO", "BIOTECH", "HARDWARE", "SOCIAL"]
STAGES  = ["SEED", "SERIES A", "SERIES B", "SERIES C", "IPO/EXIT"]

# ---------- Game State ----------
class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.firm = {
            "wealth": 0.0,
            "fund_number": 1,
            "current_size": 10.0,
        }
        self.fund = {
            "total": 10.0,
            "cash": 10.0,
            "deployed": 0.0,
            "returned": 0.0,
            "month": 1,
            "max_months": 120,
        }
        self.inbox = []
        self.portfolio = []
        self.ticks = 0
        self.game_state = "START"
        self.view_mode = "INBOX"
        self.selected_idx = 0
        self.show_details = False
        self.msg = ""
        self.msg_timer = 0
        self._startup_id = 0

    def _randf(self):
        return random.random()

    def _randi(self, lo, hi):
        return random.randint(lo, hi)

    def _next_id(self):
        self._startup_id += 1
        return self._startup_id

    def generate_startup(self):
        name = random.choice(NAMES_FIRST) + random.choice(NAMES_LAST)
        sector = random.choice(SECTORS)
        val = self._randi(2, 8) + self._randf() * 2.0
        ask_pct = self._randi(10, 20) / 100.0
        ask = val * ask_pct
        runway = self._randi(12, 24)
        burn = ask / runway
        return {
            "id": self._next_id(),
            "name": name,
            "sector": sector,
            "stage_idx": 0,
            "valuation": val,
            "ask_amt": ask,
            "ask_eq": ask_pct,
            "burn": burn,
            "runway": float(runway),
            "quality": self._randf(),
            "player_eq": 0.0,
            "player_inv": 0.0,
            "is_follow_on": False,
            "is_ma_offer": False,
            "target_idx": None,
        }

    def process_payout(self, payout):
        prev_returned = self.fund["returned"]
        self.fund["returned"] += payout
        carry = 0.0
        if self.fund["returned"] > self.fund["total"]:
            if prev_returned < self.fund["total"]:
                profit = self.fund["returned"] - self.fund["total"]
            else:
                profit = payout
            carry = profit * 0.20
        self.firm["wealth"] += carry
        self.fund["cash"] += (payout - carry)
        return carry

    def portfolio_val(self):
        return sum(p["valuation"] * p["player_eq"] for p in self.portfolio)

    def set_msg(self, text, is_good=True):
        self.msg = text
        self.msg_timer = 1

    def advance_month(self):
        self.fund["month"] += 1
        mgmt_fee = (self.fund["total"] * 0.02) / 12.0
        if self.fund["cash"] >= mgmt_fee:
            self.fund["cash"] -= mgmt_fee
            self.firm["wealth"] += mgmt_fee

        if self.fund["month"] > self.fund["max_months"]:
            self.game_state = "GAMEOVER"
            self.set_msg("FUND LIFECYCLE COMPLETE.")
            return

        i = len(self.portfolio) - 1
        while i >= 0:
            p = self.portfolio[i]
            p["runway"] -= 1
            event_roll = self._randf()

            if p["runway"] <= 0:
                if p["quality"] > 0.4 and event_roll < p["quality"] + 0.2:
                    p["stage_idx"] += 1
                    if p["stage_idx"] >= 4:
                        exit_val = p["valuation"] * (2.0 + self._randf() * 3.0)
                        payout = exit_val * p["player_eq"]
                        carry = self.process_payout(payout)
                        msg = f"EXIT! {p['name']} acquired for ${exit_val:.1f}M!"
                        if carry > 0:
                            msg += f" (CARRY: ${carry:.2f}M)"
                        self.set_msg(msg)
                        self.portfolio.pop(i)
                    else:
                        p["valuation"] *= (2.0 + self._randf() * 2.0)
                        ask_pct = self._randi(10, 20) / 100.0
                        p["ask_amt"] = p["valuation"] * ask_pct
                        p["ask_eq"] = ask_pct
                        p["runway"] = 12 + self._randi(0, 6)
                        p["burn"] = p["ask_amt"] / p["runway"]
                        p["is_follow_on"] = True
                        self.inbox.insert(0, p)
                        self.portfolio.pop(i)
                else:
                    self.set_msg(f"BANKRUPT! {p['name']} ran out of cash. (${p['player_inv']:.2f}M lost)", is_good=False)
                    self.portfolio.pop(i)
            else:
                if event_roll < 0.005:
                    self.set_msg(f"SCANDAL! {p['name']} founders arrested. Zeroed out.", is_good=False)
                    self.portfolio.pop(i)
                elif event_roll > 0.98 and p["stage_idx"] >= 1:
                    offer_val = p["valuation"] * (1.5 + self._randf())
                    offer = dict(p)
                    offer.update({
                        "is_ma_offer": True,
                        "is_follow_on": False,
                        "valuation": offer_val,
                        "ask_amt": 0.0,
                        "ask_eq": 0.0,
                        "target_idx": i,
                    })
                    self.inbox.insert(0, offer)
                    self.set_msg(f"NEW M&A OFFER FOR {p['name']}!")
            i -= 1

        if not self.inbox:
            self.inbox.append(self.generate_startup())
        elif len(self.inbox) < 5 and self._randf() < 0.7:
            self.inbox.append(self.generate_startup())

    def start_fund(self):
        self.fund["total"] = self.firm["current_size"]
        self.fund["cash"] = self.firm["current_size"]
        self.fund["deployed"] = 0.0
        self.fund["returned"] = 0.0
        self.fund["month"] = 1
        self.inbox = []
        self.portfolio = []
        for _ in range(3):
            self.inbox.append(self.generate_startup())
        self.game_state = "PLAY"
        self.view_mode = "INBOX"
        self.selected_idx = 0
        self.show_details = False
        self.set_msg(f"Fund {self.firm['fund_number']} raised: ${self.firm['current_size']:.1f}M")

    def _current_list(self):
        return self.inbox if self.view_mode == "INBOX" else self.portfolio

    def render(self):
        lines = []
        lines.append("=" * 64)
        lines.append(" AMADEUS VENTURES — TEXT EDITION")
        lines.append("=" * 64)

        if self.game_state == "START":
            lines.append("")
            lines.append("You are a first-time GP at Amadeus Ventures.")
            lines.append("Your mandate: deploy $10M over 10 years, generate returns,")
            lines.append("and build a track record to raise bigger funds.")
            lines.append("")
            lines.append("Type 'start' to raise Fund 1.")
            lines.append("Type 'help' for the command list.")
            return "\n".join(lines)

        fn = self.firm["fund_number"]
        mo = min(self.fund["month"], self.fund["max_months"])
        mx = self.fund["max_months"]
        cash = self.fund["cash"]
        ret = self.fund["returned"]
        wealth = self.firm["wealth"]
        mult = (ret + self.portfolio_val()) / self.fund["total"]

        lines.append(f" FUND {fn}  |  MONTH {mo}/{mx}  |  TVPI {mult:.2f}x")
        lines.append(f" CASH ${cash:.2f}M   RETURNED ${ret:.2f}M   YOUR WEALTH ${wealth:.2f}M")
        lines.append("-" * 64)

        ix_marker = "*" if self.view_mode == "INBOX" else " "
        pf_marker = "*" if self.view_mode == "PORTFOLIO" else " "
        lines.append(f" {ix_marker}[INBOX: {len(self.inbox)}]   {pf_marker}[PORTFOLIO: {len(self.portfolio)}]")
        lines.append("-" * 64)

        cur = self._current_list()

        if not cur:
            lines.append("")
            lines.append("  (empty) - Time will progress to accumulate deal flow.")
        elif self.show_details:
            p = cur[self.selected_idx]
            lines.append("")
            lines.append(f"  DUE DILIGENCE: {p['name']}")
            lines.append(f"  Sector : {p['sector']}")
            lines.append(f"  Stage  : {STAGES[p['stage_idx']]}")

            q = p["quality"]
            if q > 0.8: rating = "EXCELLENT"
            elif q > 0.5: rating = "GOOD"
            elif q > 0.25: rating = "AVERAGE"
            else: rating = "HIGH RISK"
            lines.append(f"  Rating : {rating}")

            if q > 0.4:
                odds = min(1.0, q + 0.2)
                odds_str = f"{odds * 100:.0f}%"
            else:
                odds_str = "0% (DOOMED)"
            lines.append(f"  Survival odds (next round): {odds_str}")
            lines.append(f"  Valuation : ${p['valuation']:.2f}M")
            lines.append(f"  Burn rate : ${p['burn']:.2f}M/mo")
            lines.append(f"  Runway    : {int(p['runway'])} mo")

            if self.view_mode == "INBOX":
                if p["is_ma_offer"]:
                    lines.append(f"  BUYOUT OFFER : ${p['valuation']:.2f}M")
                    lines.append(f"  YOUR PAYOUT  : ${p['valuation'] * p['player_eq']:.2f}M")
                else:
                    lines.append(f"  ASK AMOUNT   : ${p['ask_amt']:.2f}M")
                    lines.append(f"  FOR EQUITY   : {p['ask_eq'] * 100:.1f}%")
            else:
                lines.append(f"  YOUR INVEST  : ${p['player_inv']:.2f}M")
                lines.append(f"  YOUR EQUITY  : {p['player_eq'] * 100:.1f}%")
                lines.append(f"  CURRENT VALUE: ${p['valuation'] * p['player_eq']:.2f}M")
        else:
            start = max(0, self.selected_idx - 2)
            end = min(len(cur), start + 5)
            lines.append("")
            for i in range(start, end):
                p = cur[i]
                marker = ">" if i == self.selected_idx else " "
                title = f"{p['name']} [{p['sector']}] {STAGES[p['stage_idx']]}"
                if self.view_mode == "INBOX":
                    if p["is_ma_offer"]: title = "*M&A OFFER* " + title
                    elif p["is_follow_on"]: title = "*FOLLOW-ON* " + title
                lines.append(f"  {marker} [{i}] {title}")

                if self.view_mode == "INBOX":
                    if p["is_ma_offer"]:
                        detail = f"      buyout ${p['valuation']:.1f}M  |  payout ${p['valuation'] * p['player_eq']:.2f}M"
                    else:
                        detail = f"      val ${p['valuation']:.1f}M  |  ask ${p['ask_amt']:.2f}M for {p['ask_eq'] * 100:.1f}%"
                else:
                    detail = f"      own {p['player_eq'] * 100:.1f}%  |  runway {int(p['runway'])} mo"
                lines.append(detail)

        lines.append("-" * 64)
        if self.msg_timer > 0:
            lines.append(f" >> {self.msg}")
        elif self.game_state == "GAMEOVER":
            lines.append(" FUND LIFECYCLE COMPLETE")
            lines.append(f" Final multiple : {mult:.2f}x")
            lines.append(f" Your wealth    : ${self.firm['wealth']:.2f}M")
            lines.append(" Type 'start' to raise the next fund.")
        else:
            lines.append(" Commands: help | inbox | portfolio | select N | invest [N] | pass [N] | dd [N] | ceo [N] | advance")

        lines.append("=" * 64)
        return "\n".join(lines)

    def step(self, raw_cmd):
        self.ticks += 1
        if self.msg_timer > 0:
            self.msg_timer -= 1

        parts = (raw_cmd or "").strip().lower().split()
        if not parts:
            return self.render()

        cmd = parts[0]

        # Compound command extraction (e.g., "invest 2")
        target_idx_override = None
        if len(parts) > 1 and parts[1].isdigit():
            target_idx_override = int(parts[1])

        if cmd in ("help", "h", "?"):
            return self._help_text() + "\n\n" + self.render()
        if cmd == "quit":
            sys.exit(0)

        if self.game_state == "START":
            if cmd in ("start", "z", "begin"):
                self.start_fund()
            return self.render()

        if self.game_state == "GAMEOVER":
            if cmd in ("start", "z", "next"):
                mult = (self.fund["returned"] + self.portfolio_val()) / self.fund["total"]
                if mult >= 2.0: self.firm["current_size"] *= 3.0
                elif mult >= 1.0: self.firm["current_size"] *= 1.5
                else: self.firm["current_size"] = max(5.0, self.firm["current_size"] * 0.5)
                self.firm["fund_number"] += 1
                self.start_fund()
            return self.render()

        # View switching
        if cmd in ("inbox", "i", "1"):
            self.view_mode = "INBOX"
            self.selected_idx = target_idx_override if target_idx_override is not None else 0
            self.show_details = False
            return self.render()
        if cmd in ("portfolio", "p", "2"):
            self.view_mode = "PORTFOLIO"
            self.selected_idx = target_idx_override if target_idx_override is not None else 0
            self.show_details = False
            return self.render()

        # Selection overrides for compound commands
        cur = self._current_list()
        if target_idx_override is not None and 0 <= target_idx_override < len(cur):
            self.selected_idx = target_idx_override

        if cmd in ("dd", "details", "d"):
            self.show_details = not self.show_details
            return self.render()

        if cmd == "select" and target_idx_override is not None:
            self.show_details = False
            return self.render()
        if cmd.isdigit():
            idx = int(cmd)
            if 0 <= idx < len(cur):
                self.selected_idx = idx
                self.show_details = False
            return self.render()

        if cmd in ("up", "prev"):
            if cur:
                self.selected_idx = (self.selected_idx - 1) % len(cur)
                self.show_details = False
            return self.render()
        if cmd in ("down", "next"):
            if cur:
                self.selected_idx = (self.selected_idx + 1) % len(cur)
                self.show_details = False
            return self.render()

        if not cur:
            if cmd in ("advance", "month"):
                self.set_msg("Advancing 1 month...")
                self.advance_month()
                return self.render()
            self.set_msg("Nothing to do here. Inbox empty. Use 'advance'.", is_good=False)
            return self.render()

        p = cur[self.selected_idx]

        if cmd in ("invest", "z", "accept", "buy"):
            if self.view_mode == "INBOX":
                if p["is_ma_offer"]:
                    payout = p["valuation"] * p["player_eq"]
                    carry = self.process_payout(payout)
                    msg = f"SOLD! {p['name']} M&A payout: ${payout:.2f}M"
                    if carry > 0: msg += f" (CARRY: ${carry:.2f}M)"

                    # Hardened portfolio ID removal
                    self.portfolio = [x for x in self.portfolio if x["id"] != p["id"]]
                    self.inbox.pop(self.selected_idx)
                    self.set_msg(msg)
                else:
                    if self.fund["cash"] >= p["ask_amt"]:
                        self.fund["cash"] -= p["ask_amt"]
                        self.fund["deployed"] += p["ask_amt"]
                        p["player_eq"] += p["ask_eq"]
                        p["player_inv"] += p["ask_amt"]
                        p["is_follow_on"] = False
                        self.portfolio.append(p)
                        self.inbox.pop(self.selected_idx)
                        self.set_msg(f"INVESTED ${p['ask_amt']:.2f}M in {p['name']}")
                    else:
                        self.set_msg("INSUFFICIENT FUNDS FOR THIS ROUND.", is_good=False)

                # Check bounds and auto-advance conditionally
                if self.selected_idx >= len(self.inbox):
                    self.selected_idx = max(0, len(self.inbox) - 1)
                if len(self.inbox) == 0:
                    self.advance_month()
            return self.render()

        if cmd in ("pass", "x", "reject", "skip"):
            if self.view_mode == "INBOX":
                if p["is_ma_offer"]:
                    self.set_msg(f"Rejected M&A buyout for {p['name']}.", is_good=False)
                    self.inbox.pop(self.selected_idx)
                else:
                    if p["is_follow_on"]:
                        p["player_eq"] *= (1.0 - p["ask_eq"])
                        p["is_follow_on"] = False
                        self.portfolio.append(p)
                        self.set_msg(f"Passed on {p['name']} round. Equity diluted.", is_good=False)
                    else:
                        self.set_msg(f"Passed on {p['name']}.", is_good=False)
                    self.inbox.pop(self.selected_idx)

                # Check bounds and auto-advance conditionally
                if self.selected_idx >= len(self.inbox):
                    self.selected_idx = max(0, len(self.inbox) - 1)
                if len(self.inbox) == 0:
                    self.advance_month()
            return self.render()

        if cmd in ("ceo", "fire", "replace"):
            if self.view_mode == "PORTFOLIO":
                if p["runway"] <= 5:
                    if self.fund["cash"] >= 0.1:
                        self.fund["cash"] -= 0.1
                        p["quality"] = min(1.0, p["quality"] + 0.4)
                        p["runway"] += 6
                        p["player_eq"] *= 0.90
                        self.set_msg(f"Fired CEO of {p['name']}. Runway +6 mo, equity diluted 10%.")
                    else:
                        self.set_msg("Need $0.1M to fire CEO.", is_good=False)
                else:
                    self.set_msg("CEO replacement only available when runway <= 5 months.", is_good=False)
            return self.render()

        if cmd in ("advance", "month"):
            self.set_msg("Advancing 1 month...")
            self.advance_month()
            return self.render()

        self.set_msg(f"Unknown command: {raw_cmd!r}. Type 'help'.", is_good=False)
        return self.render()

    def _help_text(self):
        return """
COMMANDS
  inbox, i, 1        Switch to the deal inbox
  portfolio, p, 2    Switch to your portfolio
  select N, N        Select item N in the current list
  up / down          Move selection
  dd [N]             Toggle due-diligence detail view
  invest [N], z      Invest in selected deal / accept M&A offer
  pass [N], x        Pass on selected deal / reject M&A offer
  ceo [N], fire      Replace CEO of selected portfolio company
                     (only when runway <= 5 mo; costs $0.1M)
  advance            Advance one month (also triggers when inbox is emptied)
  start              Start a new fund (after game over)
  help               Show this message
  quit               Exit
"""

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
