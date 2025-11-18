from typing import List, Dict, Any

from bot_api import PokerBotAPI, PlayerAction, GameInfoAPI
from engine.cards import Card, Rank
from engine.poker_game import GameState


class SoleoBot(PokerBotAPI):

    def __init__(self, name: str):
        super().__init__(name)
        self.hands_played = 0
        self.hands_won = 0
        #can define good starting hands here

    def get_action(self, game_state, hole_cards, legal_actions, min_bet, max_bet) -> tuple:
        #poker strategy goes here
        
        return PlayerAction.CALL, 0



    # Calculate pot odds
    pot_odds = GameInfoAPI.get_pot_odds(game_state.pot, amount_to_call)

    # Get position information
    position_info = GameInfoAPI.get_position_info(game_state, self.name)

    # Check if heads-up
    is_heads_up = GameInfoAPI.is_heads_up(game_state)

    # Get opponent list
    opponents = GameInfoAPI.get_active_opponents(game_state, self.name)