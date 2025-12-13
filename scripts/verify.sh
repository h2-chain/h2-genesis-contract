VERIFIER="blockscout"
VERIFIER_URL="https://h2scan.io/api"
CHAIN_ID=2582
API_KEY="empty"

forge verify-contract --chain-id $CHAIN_ID 0x0000000000000000000000000000000000001000 contracts/ValidatorSet.sol:ValidatorSet --verifier $VERIFIER --verifier-url $VERIFIER_URL --etherscan-api-key $API_KEY --compiler-version v0.6.4

forge verify-contract --chain-id $CHAIN_ID 0x0000000000000000000000000000000000001001 contracts/SlashIndicator.sol:SlashIndicator --verifier $VERIFIER --verifier-url $VERIFIER_URL  --etherscan-api-key $API_KEY  --compiler-version v0.6.4

forge verify-contract --chain-id $CHAIN_ID 0x0000000000000000000000000000000000001004 contracts/StakeHub.sol:StakeHub --verifier $VERIFIER --verifier-url $VERIFIER_URL  --etherscan-api-key $API_KEY  --compiler-version 0.8.17