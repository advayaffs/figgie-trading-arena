"""Figgie Arena: a four-player trading experiment in one Python file.

Run: python figgie_arena.py play
     python figgie_arena.py simulate --rounds 1000 --seed 42

Arena rules: one player quotes one suit, then the other three get a chance
to trade one card. The quote expires after a fill or three passes. Seats
rotate through the quoting role. Each round starts with fresh cash.
Original game rules: https://www.figgie.com/how-to-play
"""

import argparse
import random
from math import comb, prod
from statistics import mean, stdev

SUITS = ("spades", "clubs", "hearts", "diamonds")
PARTNER = (1, 0, 3, 2)  # The other suit of the same colour.
BOTS = ("Baseline", "Hand only", "Bonus only", "Hand + bonus")
START_CASH = 350
ANTE = 50


def possible_decks():
    decks = []
    for long_suit in range(4):
        for short_suit in range(4):
            if short_suit == long_suit:
                continue
            counts = [10, 10, 10, 10]
            counts[long_suit] = 12
            counts[short_suit] = 8
            decks.append((counts, PARTNER[long_suit]))
    return decks


DECKS = possible_decks()


def goal_probabilities(opening_hand):
    """Count the ways each candidate deck could have dealt this hand."""
    weights = [0, 0, 0, 0]
    for counts, goal in DECKS:
        ways = prod(comb(total, seen) for total, seen in zip(counts, opening_hand))
        weights[goal] += ways
    total_weight = sum(weights)
    return [weight / total_weight for weight in weights]


def card_value(bot, probability, held):
    """Estimate the value of adding ONE card when we already hold 'held'."""
    if bot in ("Baseline", "Bonus only"):
        probability = 0.25

    # A deliberately simple majority-bonus heuristic. The third, fourth
    # and fifth cards may swing a close contest. These amounts are tunable.
    bonus = 0
    if bot in ("Bonus only", "Hand + bonus") and 2 <= held <= 4:
        bonus = 14
    return probability * (10 + bonus)


def bot_quote(bot, probability, held, cash, rng):
    # A seller gives up the last card in hand. A buyer adds the next one.
    shift = rng.uniform(-2, 2)
    buy_value = card_value(bot, probability, held)
    bid = min(cash, max(1, round(buy_value + shift - 1))) if cash else 0
    if not held:
        return bid, 0
    sell_value = card_value(bot, probability, held - 1)
    ask = max(1, bid + 1, round(sell_value + shift + 1))
    return bid, ask


def bot_reply(bot, probability, held, cash, bid, ask):
    buy_gain = card_value(bot, probability, held) - ask if 0 < ask <= cash else 0
    sell_gain = bid - card_value(bot, probability, held - 1) if held and bid else 0
    if buy_gain > 0 and buy_gain >= sell_gain:
        return "buy"
    if sell_gain > 0:
        return "sell"
    return "pass"


def human_quote(held, cash):
    while True:
        try:
            bid, ask = map(int, input("Your bid and ask (0 skips a side): ").split())
        except ValueError:
            print("Enter two whole numbers, for example 2 5.")
            continue
        if 0 <= bid <= cash and ask >= 0 and (held or ask == 0):
            if not ask or ask > bid:
                return bid, ask
        print("Check cash, inventory, and that the ask exceeds the bid.")


def human_reply(held, cash, bid, ask):
    options = ["pass"]
    if 0 < ask <= cash:
        options.append("buy")
    if bid and held:
        options.append("sell")
    while True:
        choice = input(" / ".join(options) + "? ").strip().lower()
        if choice in options:
            return choice


def payouts(hands, goal):
    counts = [hand[goal] for hand in hands]
    most = max(counts)
    bonus = (200 - 10 * sum(counts)) / counts.count(most)
    return [10 * count + (bonus if count == most else 0) for count in counts]


def play_round(names, turns, rng, interactive=False):
    counts, goal = rng.choice(DECKS)
    cards = [suit for suit in range(4) for _ in range(counts[suit])]
    rng.shuffle(cards)
    hands = []
    for start in range(0, 40, 10):
        dealt = cards[start:start + 10]
        hands.append([dealt.count(suit) for suit in range(4)])

    # Traded cards aren't fresh random draws. Keep the opening-hand estimate.
    beliefs = [goal_probabilities(hand) for hand in hands]
    cash = [START_CASH - ANTE] * 4
    trades = 0
    for turn in range(turns):
        maker = turn % 4
        suit = rng.randrange(4)
        if interactive:
            print(f"\nQuote {turn + 1}/{turns} | {names[maker]} | {SUITS[suit]}")
            print("Your hand:", dict(zip(SUITS, hands[0])), "| Cash:", cash[0])
        held = hands[maker][suit]
        if names[maker] == "You":
            bid, ask = human_quote(held, cash[maker])
        else:
            bid, ask = bot_quote(names[maker], beliefs[maker][suit], held, cash[maker], rng)
        if interactive:
            print(f"Bid: {bid or '-'}   Ask: {ask or '-'}")

        others = [seat for seat in range(4) if seat != maker]
        rng.shuffle(others)
        for seat in others:
            held = hands[seat][suit]
            if names[seat] == "You":
                action = human_reply(held, cash[seat], bid, ask)
            else:
                action = bot_reply(names[seat], beliefs[seat][suit], held, cash[seat], bid, ask)
            if action == "pass":
                continue
            if action == "buy":
                buyer, seller, price = seat, maker, ask
            else:
                buyer, seller, price = maker, seat, bid
            hands[seller][suit] -= 1
            hands[buyer][suit] += 1
            cash[buyer] -= price
            cash[seller] += price
            trades += 1
            if interactive:
                print(f"{names[buyer]} bought one {SUITS[suit]} card from {names[seller]} for {price}.")
            break
        else:
            if interactive:
                print("No trade.")

    awards = payouts(hands, goal)
    profits = [balance + award - START_CASH for balance, award in zip(cash, awards)]
    assert abs(sum(profits)) < 1e-8
    assert [sum(hand[s] for hand in hands) for s in range(4)] == counts
    assert min(cash) >= 0 and all(min(hand) >= 0 for hand in hands)
    if interactive:
        print(f"\nGoal suit: {SUITS[goal]} | Completed trades: {trades}")
        for name, hand, award, profit in zip(names, hands, awards, profits):
            print(f"{name:14} {hand[goal]} goal cards | payout {award:6.2f} | P&L {profit:+7.2f}")
    return profits, trades


def simulate(rounds, turns, rng):
    results = {bot: [] for bot in BOTS}
    total_trades = 0
    for _ in range(rounds):
        names = list(BOTS)
        rng.shuffle(names)
        profits, trades = play_round(names, turns, rng)
        for name, profit in zip(names, profits):
            results[name].append(profit)
        total_trades += trades

    print(f"{rounds} rounds | {total_trades / rounds:.1f} trades per round")
    print(f"{'Bot':14} {'Mean P&L':>10} {'Std error':>10}")
    for bot, profits in results.items():
        error = f"{stdev(profits) / len(profits)**0.5:.2f}" if rounds > 1 else "n/a"
        print(f"{bot:14} {mean(profits):+10.2f} {error:>10}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["play", "simulate"], nargs="?", default="simulate")
    parser.add_argument("--rounds", type=int, default=1000, help="independent simulated rounds")
    parser.add_argument("--turns", type=int, help="quote opportunities per round")
    parser.add_argument("--seed", type=int, help="set to reproduce a run")
    args = parser.parse_args()
    turns = args.turns if args.turns is not None else (16 if args.mode == "play" else 60)
    if turns < 1 or args.rounds < 1:
        parser.error("turns and rounds must be positive")
    rng = random.Random(args.seed)
    if args.mode == "play":
        print("Buy at the ask, sell at the bid. A dash means that side is closed.")
        play_round(("You", *BOTS[1:]), turns, rng, interactive=True)
    else:
        simulate(args.rounds, turns, rng)


if __name__ == "__main__":
    main()
