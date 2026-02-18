/**
 * Associate HTS Token using Hedera SDK
 * =====================================
 */
const {
    Client,
    AccountId,
    PrivateKey,
    TokenId,
    TokenAssociateTransaction
} = require("@hashgraph/sdk");

require("dotenv").config();

async function main() {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.error("Usage: node associate_hts_token.js <token_id>");
        process.exit(1);
    }

    const tokenIdStr = args[0];
    const accountIdStr = process.env.HEDERA_ACCOUNT_ID;
    let privateKeyStr = process.env.PRIVATE_KEY || process.env.PACMAN_PRIVATE_KEY;

    if (!accountIdStr || !privateKeyStr) {
        console.error("Error: HEDERA_ACCOUNT_ID or PACMAN_PRIVATE_KEY not set");
        process.exit(1);
    }

    if (privateKeyStr.startsWith("0x")) privateKeyStr = privateKeyStr.slice(2);

    try {
        const accountId = AccountId.fromString(accountIdStr);
        const privateKey = PrivateKey.fromStringECDSA(privateKeyStr);
        const client = Client.forMainnet();
        client.setOperator(accountId, privateKey);

        const tokenId = TokenId.fromString(tokenIdStr);

        console.log(`Associating token ${tokenIdStr} to account ${accountIdStr}...`);
        const transaction = new TokenAssociateTransaction()
            .setAccountId(accountId)
            .setTokenIds([tokenId]);

        const response = await transaction.execute(client);
        const receipt = await response.getReceipt(client);

        if (receipt.status.toString() === "SUCCESS") {
            console.log("✅ ASSOCIATION SUCCESSFUL!");
            process.exit(0);
        } else {
            console.error(`❌ ASSOCIATION FAILED: ${receipt.status.toString()}`);
            process.exit(1);
        }
    } catch (error) {
        if (error.message.includes("TOKEN_ALREADY_ASSOCIATED_TO_ACCOUNT")) {
            console.log("✅ Token already associated.");
            process.exit(0);
        }
        console.error(`❌ ERROR: ${error.message}`);
        process.exit(1);
    }
}

main();
