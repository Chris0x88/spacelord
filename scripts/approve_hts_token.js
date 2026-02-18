/**
 * Approve HTS Token using Hedera SDK
 * ===================================
 * 
 * This script uses the official Hedera JavaScript SDK to approve
 * HTS token allowances. This is the CORRECT way to approve HTS tokens
 * on Hedera - EVM approve() calls often fail for HTS tokens.
 * 
 * Usage:
 *   node approve_hts_token.js <token_id> <spender_id> [amount]
 * 
 * Example:
 *   node approve_hts_token.js 0.0.456858 0.0.3949434 1000000000
 * 
 * Environment variables required:
 *   - HEDERA_ACCOUNT_ID: Your Hedera account ID (e.g., 0.0.12345)
 *   - HEDERA_PRIVATE_KEY: Your ECDSA private key (hex format)
 * 
 * Install dependencies:
 *   npm install @hashgraph/sdk dotenv
 */

const {
    Client,
    AccountId,
    PrivateKey,
    TokenId,
    AccountAllowanceApproveTransaction,
    Hbar
} = require("@hashgraph/sdk");

require("dotenv").config();

async function main() {
    // Parse arguments
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.error("Usage: node approve_hts_token.js <token_id> <spender_id> [amount]");
        console.error("Example: node approve_hts_token.js 0.0.456858 0.0.3949434 1000000000");
        process.exit(1);
    }

    const tokenIdStr = args[0];
    const spenderIdStr = args[1];
    const amount = args[2] ? parseInt(args[2]) : 1000000000000; // Default: 1M tokens (6 decimals)

    // Get credentials from environment
    const accountIdStr = process.env.HEDERA_ACCOUNT_ID;
    let privateKeyStr = process.env.PRIVATE_KEY || process.env.PACMAN_PRIVATE_KEY;

    if (!accountIdStr) {
        console.error("Error: HEDERA_ACCOUNT_ID not set");
        process.exit(1);
    }
    if (!privateKeyStr) {
        console.error("Error: HEDERA_PRIVATE_KEY or PRIVATE_KEY not set");
        process.exit(1);
    }

    // Remove 0x prefix if present
    if (privateKeyStr.startsWith("0x")) {
        privateKeyStr = privateKeyStr.slice(2);
    }

    console.log("=".repeat(60));
    console.log("HTS TOKEN APPROVAL (Hedera SDK)");
    console.log("=".repeat(60));
    console.log(`Account: ${accountIdStr}`);
    console.log(`Token: ${tokenIdStr}`);
    console.log(`Spender: ${spenderIdStr}`);
    console.log(`Amount: ${amount}`);
    console.log("");

    try {
        // Create client
        const accountId = AccountId.fromString(accountIdStr);
        const privateKey = PrivateKey.fromStringECDSA(privateKeyStr);

        const client = Client.forMainnet();
        client.setOperator(accountId, privateKey);

        // Parse token and spender IDs
        const tokenId = TokenId.fromString(tokenIdStr);
        const spenderId = AccountId.fromString(spenderIdStr);

        console.log("Creating AccountAllowanceApproveTransaction...");

        // Create the approval transaction
        const transaction = new AccountAllowanceApproveTransaction()
            .approveTokenAllowance(tokenId, accountId, spenderId, amount);

        console.log("Executing transaction...");

        // Execute
        const response = await transaction.execute(client);

        console.log(`Transaction ID: ${response.transactionId.toString()}`);

        // Get receipt
        const receipt = await response.getReceipt(client);

        console.log(`Status: ${receipt.status.toString()}`);

        if (receipt.status.toString() === "SUCCESS") {
            console.log("");
            console.log("=".repeat(60));
            console.log("✅ APPROVAL SUCCESSFUL!");
            console.log("=".repeat(60));
            process.exit(0);
        } else {
            console.error("");
            console.error("=".repeat(60));
            console.error(`❌ APPROVAL FAILED: ${receipt.status.toString()}`);
            console.error("=".repeat(60));
            process.exit(1);
        }

    } catch (error) {
        console.error("");
        console.error("=".repeat(60));
        console.error(`❌ ERROR: ${error.message}`);
        console.error("=".repeat(60));
        process.exit(1);
    }
}

main();
