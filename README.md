
## What does the bot do?

- **Monitors the market**: looks for vouchers with prices below the set threshold.
- **Automatically buys**: purchases vouchers if their price meets the specified parameters.

## How to set it up?

1. **Clone the repository**:

   ```bash
   git clone https://github.com/kirillqa17/Notcoin_Voucher.git
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file**:

   In the root of the project, create a `.env` file and add the following parameters:

   ```env
   floor_gap=0.05  # Specify the difference between the current price and the target price
   collection_id=example_id  # ID of the voucher collection
   api_key=your_api_key  # Your API key
   seed=["word1", "word2", ...]  # Seed phrase in JSON format
   address=your_address  # Executor's address
   ```

4. **Change price parameters**:

   You can adjust the purchase price in the code here:

   ```python
   floor_price = 0.6
   floor_price = (floor_price - floor_gap) * 10**9 * 10
   ```

5. **Run the script**:

   ```bash
   python low_notcoin_buy.py
   ```
6. **Send all purchased NFTs to yourself**:

   In the file `transfer_nft.py`, replace the wallet address with your own and run the script.
   The script will automatically send all NFTs to one wallet.

## Important

- Make sure the data in the `.env` file is correct.
- Use the bot responsibly and adhere to the platform's rules.
