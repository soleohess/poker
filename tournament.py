"""
Poker Tournament Management System
Handles tournament structure, player elimination, and progression
"""
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging


class TournamentType(Enum):
    SINGLE_ELIMINATION = "single_elimination"
    ROUND_ROBIN = "round_robin" 
    FREEZE_OUT = "freeze_out"  # No rebuys, play until one player remains


@dataclass
class TournamentSettings:
    tournament_type: TournamentType = TournamentType.FREEZE_OUT
    starting_chips: int = 1000
    small_blind: int = 10
    big_blind: int = 20
    blind_increase_interval: int = 10  # hands
    blind_increase_factor: float = 1.5
    max_players_per_table: int = 6
    min_players_per_table: int = 2
    time_limit_per_action: float = 10.0  # seconds
    max_hands_per_level: int = 50


@dataclass
class PlayerStats:
    name: str
    chips: int = 0
    hands_played: int = 0
    hands_won: int = 0
    total_winnings: int = 0
    biggest_pot_won: int = 0
    position: int = 0
    is_eliminated: bool = False
    elimination_hand: int = 0


class TournamentTable:
    """Manages a single table in the tournament"""
    
    def __init__(self, table_id: int, players: List[str], settings: TournamentSettings):
        self.table_id = table_id
        self.players = players.copy()
        self.settings = settings
        self.eliminated_players: List[str] = []
        self.hands_played = 0
        self.current_blind_level = 1
        self.dealer_button: int = 0
        
        self.logger = logging.getLogger(f"tournament.table_{table_id}")
        
    def get_active_players(self) -> List[str]:
        """Get list of players still active at this table"""
        return [p for p in self.players if p not in self.eliminated_players]
    
    def eliminate_player(self, player: str, hand_number: int):
        """Eliminate a player from this table"""
        if player in self.players and player not in self.eliminated_players:
            self.eliminated_players.append(player)
            self.logger.info(f"Player {player} eliminated from table {self.table_id} on hand {hand_number}")
    
    def should_increase_blinds(self) -> bool:
        """Check if blinds should be increased"""
        return self.hands_played % self.settings.blind_increase_interval == 0 and self.hands_played > 0
    
    def increase_blinds(self):
        """Increase the blind levels"""
        self.current_blind_level += 1
        new_small = int(self.settings.small_blind * (self.settings.blind_increase_factor ** (self.current_blind_level - 1)))
        new_big = int(self.settings.big_blind * (self.settings.blind_increase_factor ** (self.current_blind_level - 1)))
        
        self.logger.info(f"Table {self.table_id} blinds increased to {new_small}/{new_big} (Level {self.current_blind_level})")
        return new_small, new_big
    
    def get_current_blinds(self) -> Tuple[int, int]:
        """Get current blind levels for this table"""
        small = int(self.settings.small_blind * (self.settings.blind_increase_factor ** (self.current_blind_level - 1)))
        big = int(self.settings.big_blind * (self.settings.blind_increase_factor ** (self.current_blind_level - 1)))
        return small, big
    
    def is_ready_to_break(self) -> bool:
        """Check if table should be broken up (too few players)"""
        return len(self.get_active_players()) < self.settings.min_players_per_table


class PokerTournament:
    """Manages the entire poker tournament"""
    
    def __init__(self, players: List[str], settings: TournamentSettings = None):
        self.players = players.copy()
        self.settings = settings or TournamentSettings()
        
        # Tournament state
        self.tables: Dict[int, TournamentTable] = {}
        self.player_stats: Dict[str, PlayerStats] = {}
        self.eliminated_players: List[str] = []
        self.current_hand = 0
        self.tournament_complete = False
        
        # Initialize player stats
        for player in players:
            self.player_stats[player] = PlayerStats(
                name=player, 
                chips=self.settings.starting_chips
            )
        
        self.logger = logging.getLogger("tournament")
        self.setup_tables()
    
    def setup_tables(self):
        """Set up initial tournament tables"""
        random.shuffle(self.players)  # Randomize seating
        
        players_per_table = min(self.settings.max_players_per_table, 
                               max(self.settings.min_players_per_table,
                                   len(self.players) // self.calculate_optimal_table_count()))
        
        table_id = 1
        for i in range(0, len(self.players), players_per_table):
            table_players = self.players[i:i + players_per_table]
            if len(table_players) >= self.settings.min_players_per_table:
                self.tables[table_id] = TournamentTable(table_id, table_players, self.settings)
                table_id += 1
            else:
                # Distribute remaining players to existing tables
                for j, player in enumerate(table_players):
                    target_table = (j % (table_id - 1)) + 1
                    self.tables[target_table].players.append(player)
        
        self.logger.info(f"Tournament setup with {len(self.tables)} tables")
        for table_id, table in self.tables.items():
            self.logger.info(f"Table {table_id}: {table.players}")
    
    def calculate_optimal_table_count(self) -> int:
        """Calculate optimal number of tables"""
        if len(self.players) <= self.settings.max_players_per_table:
            return 1
        
        # Try to balance table sizes
        optimal_count = math.ceil(len(self.players) / self.settings.max_players_per_table)
        
        # Ensure no table has too few players
        while optimal_count > 1:
            min_players = len(self.players) // optimal_count
            if min_players >= self.settings.min_players_per_table:
                break
            optimal_count -= 1
        
        return max(1, optimal_count)
    
    def get_active_players(self) -> List[str]:
        """Get all active players across all tables"""
        active = []
        for table in self.tables.values():
            active.extend(table.get_active_players())
        return active
    
    def eliminate_player(self, player: str, final_chips: int = 0):
        """Eliminate a player from the tournament"""
        if player in self.eliminated_players:
            return
        
        self.eliminated_players.append(player)
        self.player_stats[player].chips = final_chips
        self.player_stats[player].is_eliminated = True
        self.player_stats[player].elimination_hand = self.current_hand
        self.player_stats[player].position = len(self.players) - len(self.eliminated_players) + 1
        
        # Remove from table
        for table in self.tables.values():
            if player in table.players:
                table.eliminate_player(player, self.current_hand)
                break
        
        self.logger.info(f"Player {player} eliminated in position {self.player_stats[player].position}")
        
        # Check if tournament is complete
        if len(self.get_active_players()) <= 1:
            self.tournament_complete = True
            if self.get_active_players():
                winner = self.get_active_players()[0]
                self.player_stats[winner].position = 1
                self.logger.info(f"Tournament complete! Winner: {winner}")
    
    def update_player_chips(self, player: str, new_chip_count: int):
        """Update a player's chip count"""
        if player in self.player_stats:
            old_chips = self.player_stats[player].chips
            self.player_stats[player].chips = new_chip_count
            
            # Check for elimination
            if new_chip_count <= 0 and player not in self.eliminated_players:
                self.eliminate_player(player, 0)
    
    def record_hand_result(self, player: str, won: bool, winnings: int = 0):
        """Record the result of a hand for a player"""
        if player in self.player_stats:
            stats = self.player_stats[player]
            stats.hands_played += 1
            if won:
                stats.hands_won += 1
                stats.total_winnings += winnings
                stats.biggest_pot_won = max(stats.biggest_pot_won, winnings)
    
    def should_rebalance_tables(self) -> bool:
        """Check if tables need rebalancing"""
        active_tables = [t for t in self.tables.values() if len(t.get_active_players()) > 0]
        
        if len(active_tables) <= 1:
            return False
        
        # Check for tables that need to be broken
        for table in active_tables:
            if table.is_ready_to_break():
                return True
        
        # Check for significant imbalance
        table_sizes = [len(t.get_active_players()) for t in active_tables]
        if max(table_sizes) - min(table_sizes) > 2:
            return True
        
        return False
    
    def rebalance_tables(self):
        """Rebalance players across tables"""
        active_players = self.get_active_players()
        
        if len(active_players) <= self.settings.max_players_per_table:
            # Consolidate to single table
            self.consolidate_to_final_table(active_players)
            return
        
        # Remove empty tables
        self.tables = {tid: table for tid, table in self.tables.items() 
                      if len(table.get_active_players()) > 0}
        
        # Break tables that are too small
        tables_to_break = []
        for table_id, table in self.tables.items():
            if table.is_ready_to_break():
                tables_to_break.append(table_id)
        
        # Move players from broken tables
        displaced_players = []
        for table_id in tables_to_break:
            displaced_players.extend(self.tables[table_id].get_active_players())
            del self.tables[table_id]
        
        # Distribute displaced players
        remaining_tables = list(self.tables.values())
        for i, player in enumerate(displaced_players):
            target_table = remaining_tables[i % len(remaining_tables)]
            target_table.players.append(player)
        
        self.logger.info(f"Tables rebalanced. Active tables: {len(self.tables)}")
    
    def consolidate_to_final_table(self, players: List[str]):
        """Move all remaining players to a single final table"""
        self.tables.clear()
        self.tables[1] = TournamentTable(1, players, self.settings)
        self.logger.info(f"Consolidated to final table with {len(players)} players")
    
    def get_tournament_status(self) -> Dict[str, any]:
        """Get current tournament status"""
        active_players = self.get_active_players()
        
        return {
            'hand_number': self.current_hand,
            'total_players': len(self.players),
            'active_players': len(active_players),
            'eliminated_players': len(self.eliminated_players),
            'active_tables': len([t for t in self.tables.values() if len(t.get_active_players()) > 0]),
            'tournament_complete': self.tournament_complete,
            'chip_leader': self.get_chip_leader(),
            'average_stack': self.get_average_stack(),
            'players_remaining': active_players
        }
    
    def get_chip_leader(self) -> Optional[str]:
        """Get the current chip leader"""
        active_players = self.get_active_players()
        if not active_players:
            return None
        
        return max(active_players, key=lambda p: self.player_stats[p].chips)
    
    def get_average_stack(self) -> int:
        """Get the average chip stack of active players"""
        active_players = self.get_active_players()
        if not active_players:
            return 0
        
        total_chips = sum(self.player_stats[p].chips for p in active_players)
        return total_chips // len(active_players)
    
    def get_leaderboard(self) -> List[Tuple[str, int, int]]:
        """Get current leaderboard (name, chips, position)"""
        leaderboard = []
        
        # Active players sorted by chips
        active_players = self.get_active_players()
        active_sorted = sorted(active_players, key=lambda p: self.player_stats[p].chips, reverse=True)
        
        for i, player in enumerate(active_sorted):
            leaderboard.append((player, self.player_stats[player].chips, i + 1))
        
        # Eliminated players by elimination order (reverse)
        eliminated_sorted = sorted(self.eliminated_players, 
                                 key=lambda p: self.player_stats[p].position)
        
        for player in eliminated_sorted:
            leaderboard.append((player, self.player_stats[player].chips, self.player_stats[player].position))
        
        return leaderboard
    
    def advance_hand(self):
        """Advance to the next hand"""
        self.current_hand += 1
        
        # Increase blinds if necessary
        for table in self.tables.values():
            table.hands_played += 1
    
    def is_tournament_complete(self) -> bool:
        """Check if tournament is complete"""
        return self.tournament_complete or len(self.get_active_players()) <= 1
    
    def get_final_results(self) -> List[Tuple[str, int, int]]:
        """Get final tournament results"""
        return self.get_leaderboard()