# Homomorphic Battleship

A secure implementation of the classic Battleship game using **Homomorphic Encryption**. This project demonstrates how two parties can play a game with hidden states (the board) while verifying the game's integrity and win conditions mathematically without revealing secret ship locations.

## Prerequisites

You need Python 3 installed on your system. This project relies on the `phe` library for the Paillier Cryptosystem.

### Installation

1.  **Clone or Download** this repository to your local machine.
2.  **Install Dependencies** using pip:

    pip install phe   

## How to Run

1.  Navigate to the project folder in your terminal.
2.  Run the game script:

    python game.py

3.  **Gameplay:**
    * You are **Alice**.
    * **Bob** is the computer opponent.
    * Follow the on-screen prompts to enter attack coordinates (e.g., `A5`, `B2`).
    * The game continues until one player's fleet is completely destroyed.

## Why Homomorphic Encryption?

In a standard digital Battleship game, the computer has to "know" where your ships are to tell you if you've been hit. This creates a trust issue: *How do you know the computer isn't cheating?*

In this implementation, the board state is encrypted using the **Paillier Cryptosystem**. This allows us to perform mathematical operations on the encrypted data without ever decrypting it.

### 1. Secure State Storage
* **0 = Water**, **1 = Ship**.
* The entire 10x10 board is encrypted at the start. The game logic stores a matrix of **Encrypted Objects**.
* Looking at the memory reveals nothing about where the ships are.

### 2. Homomorphic Updates (The "Hit" Logic)
When a player lands a hit on a ship, we need to update the board state from `1` (Ship) to `0` (Destroyed). However, we cannot decrypt the cell to change it.

Instead, we use the **Additive Homomorphic Property**:
> `Enc(A) + Enc(B) = Enc(A + B)`

To mark a ship as destroyed, we add an encrypted `-1` to the cell:
> `Enc(1) + Enc(-1) = Enc(1 + -1) = Enc(0)`

This mathematically updates the game state to "Destroyed" without anyone seeing the underlying values.

### 3. Zero-Knowledge Win Condition
How do we know if a player has lost without checking every cell?
We use Homomorphic Summation. By summing every encrypted cell on the board, we get an encrypted total of the remaining health:

> `Sum(Encified_Board) = Enc(Total_Health)`

At the end of every turn, we decrypt **only this sum**.
* If the decrypted sum is `> 0`, ships are still afloat.
* If the decrypted sum is `0`, all ships have been destroyed.

This allows the referee to verify the winner **without ever learning the location of the surviving ships**.

## Project Structure

* `game.py`: The main game logic, including the `Player` class and Homomorphic Encryption operations.
* `README.md`: This documentation file.
