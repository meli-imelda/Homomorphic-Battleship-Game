import random 
import sys    
import time   
from phe import paillier 

# --- CONFIGURATION ---
GRID_SIZE = 10  # size of the game board 10x10.
SHIP_SIZES = [5, 4, 3, 2, 2] # ship lengths to be placed on the board.

class Player: # represents a player in the game.
    def __init__(self, name): 
        self.name = name
        
        # 1. Generate Keys (The "Trust" Setup)
        print(f"[{name}] Generating Paillier Keypair to protect my board)")
        self.public_key, self.private_key = paillier.generate_paillier_keypair() # generate public/private keypair for HE.
        
        # 2. Setup Boards
        # plain_grid: Used for logic checks (is there a ship here?)
        # a 10x10 grid filled with 0s. 0 represents water, 1 will represent a ship.
        self.plain_grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        
        # encrypted_grid: The real game state stored in the 'cloud' (Network)
        # This grid will eventually hold the encrypted values corresponding to the plain_grid.
        self.encrypted_grid = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)] # Initialize the encrypted grid with None placeholders.
        
        # guesses: What the opponent sees (Hits/Misses)
        # This grid tracks the history of attacks against this player.
        self.guess_board = [['.' for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)] # Initialize the visual tracking board with dots.
        
        self.place_ships() # Call the method to randomly place ships on the plain_grid.
        self.encrypt_initial_board() # Call the method to encrypt the plain_grid into the encrypted_grid.

    def place_ships(self): # Method to handle random ship placement.
        """Randomly places ships on the plain_grid."""
        for size in SHIP_SIZES: # Loop through each ship size defined in the configuration.
            placed = False # Flag to track if the current ship has been successfully placed.
            while not placed: # Keep trying until the current ship is placed.
                orientation = random.choice(['H', 'V']) # Randomly choose 'H' (Horizontal) or 'V' (Vertical) orientation.
                row = random.randint(0, GRID_SIZE - 1) 
                col = random.randint(0, GRID_SIZE - 1) 
                # Check if the chosen position is valid (no overlaps, within bounds).
                if self.is_valid_placement(row, col, size, orientation): 
                    self.set_ship(row, col, size, orientation) # If valid, place the ship on the plain_grid.
                    placed = True # Set flag to True to exit the while loop and move to the next ship.
        print(f"[{self.name}] Ships placed on secret board.") # Confirm to the console that ships are placed.

    def is_valid_placement(self, row, col, size, orientation): # Validate ship position.
        if orientation == 'H': 
            if col + size > GRID_SIZE: return False # If the ship extends past the right edge, it's invalid.
            for c in range(col, col + size): 
                if self.plain_grid[row][c] == 1: return False # If any cell is already 1 (occupied), it's invalid.
        else: # Check logic for Vertical placement.
            if row + size > GRID_SIZE: return False # If the ship extends past the bottom edge, it's invalid.
            for r in range(row, row + size): 
                if self.plain_grid[r][col] == 1: return False # If any cell is already 1 (occupied), it's invalid.
        return True # If no checks failed, the placement is valid.

    def set_ship(self, row, col, size, orientation): # Write the ship to the grid.
        if orientation == 'H': 
            for c in range(col, col + size): 
                self.plain_grid[row][c] = 1 # Set the cell value to 1 (indicating a ship part).
        else: # For Vertical orientation...
            for r in range(row, row + size): 
                self.plain_grid[r][col] = 1 # Set the cell value to 1 (indicating a ship part).

    def encrypt_initial_board(self): # Perform the initial encryption of the board.
        """
        Converts the plain 1s (Ships) and 0s (Water) into Paillier Encrypted objects.
        This represents the 'Network Job' from the simplified example.
        """
        print(f"   [{self.name}] Encrypting board state to send to Game Network...") # Status update.
        for r in range(GRID_SIZE): 
            for c in range(GRID_SIZE):
                # Encrypting 0 or 1
                val = self.plain_grid[r][c] # Get the plaintext value (0 or 1) from the plain grid.
                # Encrypt the value using the player's public key.
                # This creates an EncryptedNumber object that hides the value.
                self.encrypted_grid[r][c] = self.public_key.encrypt(val) 

    def receive_attack(self, row, col): # Method to handle being attacked by the opponent.
        """
        Processes an incoming attack.
        Returns: True if Hit, False if Miss.
        """
        # Check plaintext for Hit/Miss logic.
        is_hit = self.plain_grid[row][col] == 1 
        
        # Mark the visual board so the opponent knows the result.
        # 'X' represents a hit, 'O' represents a miss.
        self.guess_board[row][col] = 'X' if is_hit else 'O'
        
        if is_hit: # If the attack hit a ship...
            # --- HOMOMORPHIC MATH ---
            # If hit, remove the ship part from the ENCRYPTED board.
            # Current Cell is Enc(1). We want it to become Enc(0).
            # Enc(A) + Enc(B) = Enc(A + B).
            # Enc(1) + Enc(-1) = Enc(1 - 1) = Enc(0).
            # Without decrypting the cell
            
            # Create an encrypted representation of -1 using the public key.
            minus_one = self.public_key.encrypt(-1) 
            
            # Add the encrypted -1 to the current encrypted cell.
            # Because of homomorphic properties, this subtracts 1 from the underlying value.
            self.encrypted_grid[row][col] = self.encrypted_grid[row][col] + minus_one
            
            # Update plain grid for logic consistency (so we don't count it as a ship later).
            self.plain_grid[row][col] = 0 
            
        return is_hit # Return whether the attack was a hit or not.

    def check_health_homomorphically(self): # Check if the player is still alive using HE.
        """
        The critical HE verification step.
        Sums the ENCRYPTED grid. Decrypts ONLY the sum.
        """
        # Initialize an accumulator sum with an encrypted 0.
        encrypted_total = self.public_key.encrypt(0)
        
        # Add every cell in the encrypted grid to the total.
        for r in range(GRID_SIZE): 
            for c in range(GRID_SIZE):
                # Homomorphic Addition: Enc(Total) + Enc(Cell) = Enc(Total + Cell_Value)
                encrypted_total = encrypted_total + self.encrypted_grid[r][c]
        
        # Decrypt the final sum using the private key.
        # This reveals the total number of '1's (ship parts) left on the board,
        # without revealing their specific locations.
        total_health = self.private_key.decrypt(encrypted_total)
        return total_health # Return the integer count of remaining ship parts.

    def print_board_view(self): # Print the board state (Hits/Misses).
        print(f"\n--- {self.name}'s Board Status ---") 
        # Print column numbers (1-10) for reference.
        print("   " + " ".join([str(i+1) for i in range(GRID_SIZE)]))
        for r in range(GRID_SIZE):
            row_label = chr(65 + r) # Convert row index (0-9) to letter (A-J).
            # Print the row label and the row's contents joined by pipes.
            print(f"{row_label} |" + "|".join(self.guess_board[r]) + "|")

# --- UTILITIES ---
def get_coordinates(): # Get valid user input.
    while True: # Infinite loop until valid input is received.
        try:
            # Prompt user for input, convert to uppercase, and strip whitespace.
            user_input = input("Enter coordinates (e.g., A5): ").upper().strip()
            if len(user_input) < 2: continue # If input is too short, restart loop.
            
            row_char = user_input[0] # The first character is the row (Letter).
            col_str = user_input[1:] # The rest is the column (Number).
            
            # Validate that the first char is a letter and the rest is a number.
            if not row_char.isalpha() or not col_str.isdigit():
                print("Invalid format.")
                continue
                
            # Convert row letter to index (A=0, B=1, etc.) using ASCII values.
            row = ord(row_char) - 65
            # Convert column string to index (1=0, 2=1, etc.).
            col = int(col_str) - 1
            
            # Check if calculated indices are within the 10x10 grid limits.
            if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
                return row, col # Return valid indices.
            else:
                print("Coordinates out of bounds.") # Error message.
        except ValueError: # Catch any conversion errors.
            pass

def main(): 
    print("=============================================")
    print("   HOMOMORPHIC BATTLESHIP    ")
    print("=============================================\n")

    # 1. Setup
    alice = Player("Alice") # Create Player Alice (User).
    bob = Player("Bob") # Create Player Bob (Computer).
    
    turn_count = 0 # Initialize turn counter.
    game_over = False # Initialize game over flag.

    while not game_over: 
        turn_count += 1 # Increment turn.
        # Determine who attacks whom based on turn count (Alice odd, Bob even).
        attacker = alice if turn_count % 2 != 0 else bob
        defender = bob if turn_count % 2 != 0 else alice

        print(f"\n=== TURN {turn_count}: {attacker.name} attacks {defender.name} ===")
        
        # Show what the attacker sees of the defender's board (the guess_board).
        defender.print_board_view()

        # Get Attack Coordinates
        row, col = 0, 0
        if attacker.name == "Alice": # If it's Alice's turn...
            row, col = get_coordinates() # Ask user for input.
        else: # If it's Bob's turn (Computer)...
            # Bob guesses randomly, but logic ensures he doesn't guess the same spot twice.
            while True:
                row, col = random.randint(0, 9), random.randint(0, 9)
                if defender.guess_board[row][col] == '.': # Check if spot is un-guessed.
                    break # Valid guess found.
            print(f"Bob guesses: {chr(65+row)}{col+1}") # Announce Bob's guess.
            time.sleep(1) # Small delay for better UX.

        # Process Attack
        # Check if the chosen coordinate was already guessed (redundant for Bob, useful for Alice).
        if defender.guess_board[row][col] != '.':
            print("Position already attacked! Wasted turn.")
        else:
            # Call receive_attack on defender to check hit/miss and update HE grid.
            is_hit = defender.receive_attack(row, col)
            if is_hit:
                print(f"*** WAOUH! {attacker.name} scored a HIT! ***")
                # Visual flair explaining the invisible homomorphic update happening.
                print(f"   (Network: Updating Encrypted Cell {chr(65+row)}{col+1} via Homomorphic Addition...)")
            else:
                print(f"--- OH OH!. {attacker.name} missed. ---")

        # --- THE WIN CHECK ---
        # Verify by summing the encrypted values.
        print(f"   [Referee] Verifying {defender.name}'s remaining life securely...")
        
        # Calculate remaining life using the encrypted grid summation.
        remaining_life = defender.check_health_homomorphically()
        print(f"   [Referee Decrypts] {defender.name} has {remaining_life} ship parts remaining.")

        # Check win condition
        if remaining_life == 0:
            print(f"\nGAME OVER! {attacker.name} wins!")
            game_over = True # Set flag to end loop.

if __name__ == "__main__": 
    try:
        main() 
    except KeyboardInterrupt: 
        print("\nGame exited.")
        sys.exit()