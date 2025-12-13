const web3 = require("web3");
const RLP = require("rlp");

// Configure
const validators = [
  {
    consensusAddr: "0x563322cc646B29348998b48f0A781a72de0E885B",
    feeAddr: "0x563322cc646B29348998b48f0A781a72de0E885B",
    bbcFeeAddr: "0x563322cc646B29348998b48f0A781a72de0E885B",
    votingPower: 0x0000000000000064,
  },
  {
    consensusAddr: "0x4dDf403FAb2C9953e87b713AF8650b47a506E4e3",
    feeAddr: "0x4dDf403FAb2C9953e87b713AF8650b47a506E4e3",
    bbcFeeAddr: "0x4dDf403FAb2C9953e87b713AF8650b47a506E4e3",
    votingPower: 0x0000000000000064,
  },
  {
    consensusAddr: "0xE1094a64b9E6A35CF504D97782084Dd0208E49A8",
    feeAddr: "0xE1094a64b9E6A35CF504D97782084Dd0208E49A8",
    bbcFeeAddr: "0xE1094a64b9E6A35CF504D97782084Dd0208E49A8",
    votingPower: 0x0000000000000064,
  },
  {
    consensusAddr: "0xEf5e9dE1e55cCe5c86A19D71A9EEbEc286394b33",
    feeAddr: "0xEf5e9dE1e55cCe5c86A19D71A9EEbEc286394b33",
    bbcFeeAddr: "0xEf5e9dE1e55cCe5c86A19D71A9EEbEc286394b33",
    votingPower: 0x0000000000000064,
  },
  {
    consensusAddr: "0xE11fe867Fff43D89465b8d2e0DB05DEE5504d7ce",
    feeAddr: "0xE11fe867Fff43D89465b8d2e0DB05DEE5504d7ce",
    bbcFeeAddr: "0xE11fe867Fff43D89465b8d2e0DB05DEE5504d7ce",
    votingPower: 0x0000000000000064,
  },
  {
    consensusAddr: "0x4ED4C4aA45a69C5BE22c2CA646Db0887b266B862",
    feeAddr: "0x4ED4C4aA45a69C5BE22c2CA646Db0887b266B862",
    bbcFeeAddr: "0x4ED4C4aA45a69C5BE22c2CA646Db0887b266B862",
    votingPower: 0x0000000000000064,
  },
  {
    consensusAddr: "0x4615415aac8609577C4A2aDd55af25FECF5F862f",
    feeAddr: "0x4615415aac8609577C4A2aDd55af25FECF5F862f",
    bbcFeeAddr: "0x4615415aac8609577C4A2aDd55af25FECF5F862f",
    votingPower: 0x0000000000000064,
  },
  {
    consensusAddr: "0x2E7AC7Fb5c3Ccb279b5C1168a117b4D0f3Fb2cD2",
    feeAddr: "0x2E7AC7Fb5c3Ccb279b5C1168a117b4D0f3Fb2cD2",
    bbcFeeAddr: "0x2E7AC7Fb5c3Ccb279b5C1168a117b4D0f3Fb2cD2",
    votingPower: 0x0000000000000064,
  },
  {
    consensusAddr: "0x632Aab1eD1054D2A43d4077662ABee5557e46457",
    feeAddr: "0x632Aab1eD1054D2A43d4077662ABee5557e46457",
    bbcFeeAddr: "0x632Aab1eD1054D2A43d4077662ABee5557e46457",
    votingPower: 0x0000000000000064,
  },
];
const bLSPublicKeys = [
  "0x93c6fb41d8897eb68ad25e966de3cb309cbf1807da6e3032a88707fb80c9e4a98f110f72f6b7bba588c2c38017d8eab7",
  "0xa6450af15c45c559954660cf3d01d8cf6ed93c8f4a2ae147363274ceb21252bfc3544841ac5e63fd62508e544e3bd63a",
  "0x90dc7f1c9792e2d2ab1461ee15c612d70b79819c24b3eaf74bee343e61766e02bfc912257e593955651d35ec14de3612",
  "0x9722fc855ae18ea61969c26f0fccd93296cc47d07e7e9d0ce445c6ee6a1d14eb2e7fef75dcd41bf4b0bca8ac95738ada",
  "0x93bc9190bf418f4f20db8c31f3111010138fcbdd6e3e98d5e360e4237d3eca4fef1aa39552557d8e812c86e6c4979933",
  "0x937bb0f0b8f504c3397b774f9d5e7127f4b9c15fda859410e873d55c4bdbd014566e082d9a1c8a1c38f36a634fbdd25b",
  "0x81fbeb9dbca53bdc16da942059eb5327aac6c2929ae3b0348d5c55b786e2e44d32bc68483ddc3a4bb8dc598c41bdc396",
  "0x90fbc2dc507a55c5dec905aa093b22b2956eb12e8cd861b2150b1077822ff4b0892cd363c5e68994fc37eacba4106609",
  "0xb892aff71e0f9537e70adb94a80876c4b7f4859bac606f76fff6f08f30f0363ee2bc3e4a65f9b993b27c655657f69f49",
];

// ======== Do not edit below ========
function generateExtraData(validators) {
  let extraVanity = Buffer.alloc(32);
  let validatorsBytes = extraDataSerialize(validators);
  let extraSeal = Buffer.alloc(65);
  return Buffer.concat([extraVanity, validatorsBytes, extraSeal]);
}

function extraDataSerialize(validators) {
  let n = validators.length;
  let arr = [];
  for (let i = 0; i < n; i++) {
    let validator = validators[i];
    arr.push(Buffer.from(web3.utils.hexToBytes(validator.consensusAddr)));
  }
  return Buffer.concat(arr);
}

function validatorUpdateRlpEncode(validators, bLSPublicKeys) {
  let n = validators.length;
  let vals = [];
  for (let i = 0; i < n; i++) {
    vals.push([
      validators[i].consensusAddr,
      validators[i].bbcFeeAddr,
      validators[i].feeAddr,
      validators[i].votingPower,
      bLSPublicKeys[i],
    ]);
  }
  let pkg = [0x00, vals];
  return web3.utils.bytesToHex(RLP.encode(pkg));
}

extraValidatorBytes = generateExtraData(validators);
// init_validator_set_bytes
validatorSetBytes = validatorUpdateRlpEncode(validators, bLSPublicKeys);
console.log("init_validator_set_bytes:", validatorSetBytes);

exports = module.exports = {
  extraValidatorBytes: extraValidatorBytes,
  validatorSetBytes: validatorSetBytes,
};
