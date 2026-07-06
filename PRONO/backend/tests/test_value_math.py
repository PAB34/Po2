import unittest

from app.value.blocks import EventBlock, Selection, independent_blocks_probability
from app.value.clv import clv
from app.value.ev import (
    boosted_odds,
    break_even_probability,
    selection_ev,
    ticket_ev,
)
from app.value.odds import devig_proportional, implied_probability
from app.value.tickets import evaluate_ticket


class ValueMathTests(unittest.TestCase):
    def test_implied_probability(self):
        self.assertAlmostEqual(implied_probability(1.25), 0.80, places=6)

    def test_devig_two_way_market(self):
        result = devig_proportional([1.25, 4.20])
        self.assertAlmostEqual(result.overround, 1.038095238, places=6)
        self.assertAlmostEqual(result.probabilities[0], 0.7706422018, places=6)
        self.assertAlmostEqual(result.probabilities[1], 0.2293577982, places=6)

    def test_selection_ev(self):
        self.assertAlmostEqual(selection_ev(0.88, 1.16), 0.0208, places=6)

    def test_clv(self):
        self.assertAlmostEqual(clv(1.25, 1.18), 0.0593220339, places=6)

    def test_boosted_ticket_odds(self):
        self.assertAlmostEqual(boosted_odds(15.0, 0.16), 17.40, places=6)

    def test_break_even_probability_for_boosted_odds(self):
        self.assertAlmostEqual(break_even_probability(17.40), 0.0574712644, places=6)

    def test_ticket_ev(self):
        self.assertAlmostEqual(ticket_ev(0.06, 17.40), 0.044, places=6)

    def test_same_match_multiple_selections_require_joint_probability(self):
        selections = [
            Selection(event_id="match-1", market="1N2", name="Team A wins", probability=0.58, odd=1.70),
            Selection(event_id="match-1", market="total_goals", name="Over 1.5", probability=0.74, odd=1.28),
            Selection(event_id="match-1", market="team_goal", name="Team A scores", probability=0.82, odd=1.14),
        ]
        block = EventBlock.from_selections(selections)
        with self.assertRaisesRegex(ValueError, "joint probability"):
            block.probability()

    def test_same_match_block_uses_explicit_joint_probability(self):
        selections = [
            Selection(event_id="match-1", market="1N2", name="Team A wins", probability=0.58, odd=1.70),
            Selection(event_id="match-1", market="total_goals", name="Over 1.5", probability=0.74, odd=1.28),
        ]
        block = EventBlock.from_selections(selections, joint_probability=0.51)
        self.assertAlmostEqual(block.probability(), 0.51, places=6)
        self.assertAlmostEqual(block.combined_odds(), 2.176, places=6)

    def test_ticket_probability_multiplies_independent_blocks_only(self):
        block_a = EventBlock.from_selections([
            Selection(event_id="match-1", market="1N2", name="Team A wins", probability=0.60, odd=1.60)
        ])
        block_b = EventBlock.from_selections([
            Selection(event_id="match-2", market="tennis", name="Player B wins", probability=0.70, odd=1.35)
        ])
        self.assertAlmostEqual(independent_blocks_probability([block_a, block_b]), 0.42, places=6)

    def test_ticket_rejects_duplicate_event_blocks(self):
        block_a = EventBlock.from_selections([
            Selection(event_id="match-1", market="1N2", name="Team A wins", probability=0.60, odd=1.60)
        ])
        block_b = EventBlock.from_selections([
            Selection(event_id="match-1", market="over", name="Over 1.5", probability=0.75, odd=1.25)
        ])
        with self.assertRaisesRegex(ValueError, "single block"):
            independent_blocks_probability([block_a, block_b])

    def test_evaluate_ticket(self):
        blocks = [
            EventBlock.from_selections([
                Selection(event_id="match-1", market="1N2", name="Team A wins", probability=0.60, odd=1.60)
            ]),
            EventBlock.from_selections([
                Selection(event_id="match-2", market="tennis", name="Player B wins", probability=0.70, odd=1.35)
            ]),
        ]
        evaluation = evaluate_ticket(blocks, boost_rate=0.10)
        self.assertAlmostEqual(evaluation.raw_odds, 2.16, places=6)
        self.assertAlmostEqual(evaluation.boosted_odds, 2.376, places=6)
        self.assertAlmostEqual(evaluation.probability, 0.42, places=6)
        self.assertAlmostEqual(evaluation.ev, -0.00208, places=6)


if __name__ == "__main__":
    unittest.main()
