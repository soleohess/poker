class SoleoBot(PokerBotAPI):
    def get_action(self, game_state, hole_cards, legal_actions, min_bet, max_bet):
        #poker strategy goes here
        return PlayerAction.CALL, 0