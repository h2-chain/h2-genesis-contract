pragma solidity ^0.8.10;

import "./utils/Deployer.sol";

contract ValidatorSetTest is Deployer {
    using RLPEncode for *;

    event validatorSetUpdated();
    event systemTransfer(uint256 amount);
    event RewardDistributed(address indexed operatorAddress, uint256 reward);
    event deprecatedDeposit(address indexed validator, uint256 amount);
    event validatorDeposit(address indexed validator, uint256 amount);
    event failReasonWithStr(string message);
    event finalityRewardDeposit(address indexed validator, uint256 amount);
    event deprecatedFinalityRewardDeposit(address indexed validator, uint256 amount);
    event unsupportedPackage(uint64 indexed packageSequence, uint8 indexed channelId, bytes payload);

    uint256 public totalInComing;
    uint256 public burnRatio;
    uint256 public burnRatioScale;
    uint256 public maxNumOfWorkingNeutrons;
    uint256 public numOfProtons;
    uint256 public systemRewardBaseRatio;
    uint256 public systemRewardRatioScale;

    address public coinbase;
    address public validator0;
    mapping(address => bool) public protons;

    function setUp() public {
        // add operator
        bytes memory key = "addOperator";
        bytes memory valueBytes = abi.encodePacked(address(validatorSet));
        vm.expectEmit(false, false, false, true, address(systemReward));
        emit paramChange(string(key), valueBytes);
        _updateParamByGovHub(key, valueBytes, address(systemReward));
        assertTrue(systemReward.isOperator(address(validatorSet)));

        burnRatio =
            validatorSet.isSystemRewardIncluded() ? validatorSet.burnRatio() : validatorSet.INIT_BURN_RATIO();
        burnRatioScale = validatorSet.BLOCK_FEES_RATIO_SCALE();
        systemRewardBaseRatio = validatorSet.isSystemRewardIncluded()
            ? validatorSet.systemRewardBaseRatio()
            : validatorSet.INIT_SYSTEM_REWARD_RATIO();
        systemRewardRatioScale = validatorSet.BLOCK_FEES_RATIO_SCALE();
        totalInComing = validatorSet.totalInComing();
        maxNumOfWorkingNeutrons = validatorSet.maxNumOfWorkingNeutrons();
        numOfProtons = validatorSet.numOfProtons();

        address[] memory validators = validatorSet.getValidators();
        validator0 = validators[0];

        coinbase = block.coinbase;
        vm.deal(coinbase, 100 ether);

        // set gas price to zero to send system slash tx
        vm.txGasPrice(0);
        vm.mockCall(address(0x66), bytes(""), hex"01");
    }

    function testDeposit(uint256 amount) public {
        vm.assume(amount >= 1e16);
        vm.assume(amount <= 1e19);

        vm.expectRevert("the message sender must be the block producer");
        validatorSet.deposit{ value: amount }(validator0);

        vm.startPrank(coinbase);
        vm.expectRevert("deposit value is zero");
        validatorSet.deposit(validator0);

        uint256 realAmount0 = _calcIncoming(amount);
        vm.expectEmit(true, false, false, true, address(validatorSet));
        emit validatorDeposit(validator0, realAmount0);
        validatorSet.deposit{ value: amount }(validator0);

        vm.stopPrank();
        assertEq(validatorSet.getTurnLength(), 16);
        bytes memory key = "turnLength";
        bytes memory value = bytes(hex"0000000000000000000000000000000000000000000000000000000000000005"); // 5
        _updateParamByGovHub(key, value, address(validatorSet));
        assertEq(validatorSet.getTurnLength(), 5);

        key = "systemRewardAntiMEVRatio";
        value = bytes(hex"0000000000000000000000000000000000000000000000000000000000000200"); // 512
        _updateParamByGovHub(key, value, address(validatorSet));
        assertEq(validatorSet.systemRewardAntiMEVRatio(), 512);
        vm.startPrank(coinbase);

        uint256 realAmount1 = _calcIncoming(amount);
        vm.expectEmit(true, false, false, true, address(validatorSet));
        emit validatorDeposit(validator0, realAmount1);
        validatorSet.deposit{ value: amount }(validator0);

        address newAccount = _getNextUserAddress();
        vm.expectEmit(true, false, false, true, address(validatorSet));
        emit deprecatedDeposit(newAccount, realAmount1);
        validatorSet.deposit{ value: amount }(newAccount);

        assertEq(validatorSet.totalInComing(), totalInComing + realAmount0 + realAmount1);
        vm.stopPrank();
    }

    function testGov() public {
        bytes memory key = "maxNumOfWorkingNeutrons";
        bytes memory value = bytes(hex"0000000000000000000000000000000000000000000000000000000000000015"); // 21
        vm.expectEmit(false, false, false, true, address(govHub));
        emit failReasonWithStr("the maxNumOfWorkingNeutrons must be not greater than maxNumOfNeutrons");
        _updateParamByGovHub(key, value, address(validatorSet));
        assertEq(validatorSet.maxNumOfWorkingNeutrons(), maxNumOfWorkingNeutrons);

        value = bytes(hex"000000000000000000000000000000000000000000000000000000000000000a"); // 10
        _updateParamByGovHub(key, value, address(validatorSet));
        assertEq(validatorSet.maxNumOfWorkingNeutrons(), 10);

        key = "maxNumOfNeutrons";
        value = bytes(hex"0000000000000000000000000000000000000000000000000000000000000005"); // 5
        _updateParamByGovHub(key, value, address(validatorSet));
        assertEq(validatorSet.maxNumOfNeutrons(), 5);
        assertEq(validatorSet.maxNumOfWorkingNeutrons(), 5);

        key = "systemRewardBaseRatio";
        value = bytes(hex"0000000000000000000000000000000000000000000000000000000000000400"); // 1024
        _updateParamByGovHub(key, value, address(validatorSet));
        assertEq(validatorSet.systemRewardBaseRatio(), 1024);
    }

    function testValidateSetChange() public {
        for (uint256 i; i < 5; ++i) {
            (, address[] memory consensusAddrs, uint64[] memory votingPowers, bytes[] memory voteAddrs) =
                _batchCreateValidators(5);
            vm.prank(coinbase);
            validatorSet.updateValidatorSetV2(consensusAddrs, votingPowers, voteAddrs);

            address[] memory valSet = validatorSet.getValidators();
            for (uint256 j; j < 5; ++j) {
                assertEq(valSet[j], consensusAddrs[j], "consensus address not equal");
                assertTrue(validatorSet.isCurrentValidator(consensusAddrs[j]), "the address should be a validator");
            }
        }
    }

    function testGetMiningValidatorsWith41Vals() public {
        (, address[] memory consensusAddrs, uint64[] memory votingPowers, bytes[] memory voteAddrs) =
            _batchCreateValidators(41);
        vm.prank(coinbase);
        validatorSet.updateValidatorSetV2(consensusAddrs, votingPowers, voteAddrs);

        address[] memory vals = validatorSet.getValidators();
        (address[] memory miningVals,) = validatorSet.getMiningValidators();

        uint256 count;
        uint256 _numOfProtons;
        uint256 _maxNumOfWorkingNeutrons = maxNumOfWorkingNeutrons;
        if (numOfProtons == 0) {
            _numOfProtons = validatorSet.INIT_NUM_OF_PROTONS();
        } else {
            _numOfProtons = numOfProtons;
        }
        if ((vals.length - _numOfProtons) < _maxNumOfWorkingNeutrons) {
            _maxNumOfWorkingNeutrons = vals.length - _numOfProtons;
        }

        for (uint256 i; i < _numOfProtons; ++i) {
            protons[vals[i]] = true;
        }
        for (uint256 i; i < _numOfProtons; ++i) {
            if (!protons[miningVals[i]]) {
                ++count;
            }
        }
        assertGe(_maxNumOfWorkingNeutrons, count);
        assertGe(count, 0);
    }

    function testDistributeAlgorithm() public {
        (
            address[] memory operatorAddrs,
            address[] memory consensusAddrs,
            uint64[] memory votingPowers,
            bytes[] memory voteAddrs
        ) = _batchCreateValidators(1);

        vm.startPrank(coinbase);
        validatorSet.updateValidatorSetV2(consensusAddrs, votingPowers, voteAddrs);

        address val = consensusAddrs[0];
        address deprecated = _getNextUserAddress();
        vm.deal(address(validatorSet), 0);

        for (uint256 i; i < 5; ++i) {
            validatorSet.deposit{ value: 1 ether }(val);
            validatorSet.deposit{ value: 1 ether }(deprecated);
            validatorSet.deposit{ value: 0.1 ether }(val);
            validatorSet.deposit{ value: 0.1 ether }(deprecated);
        }

        uint256 expectedBalance = _calcIncoming(11 ether);
        uint256 expectedIncoming = _calcIncoming(5.5 ether);
        uint256 balance = address(validatorSet).balance;
        uint256 incoming = validatorSet.totalInComing();
        assertEq(balance, expectedBalance);
        assertEq(incoming, expectedIncoming);

        vm.expectEmit(true, false, false, true, address(stakeHub));
        emit RewardDistributed(operatorAddrs[0], expectedIncoming);
        vm.expectEmit(false, false, false, true, address(validatorSet));
        emit systemTransfer(expectedBalance - expectedIncoming);
        vm.expectEmit(false, false, false, false, address(validatorSet));
        emit validatorSetUpdated();
        validatorSet.updateValidatorSetV2(consensusAddrs, votingPowers, voteAddrs);

        vm.stopPrank();
    }

    function testMassiveDistribute() public {
        (
            address[] memory operatorAddrs,
            address[] memory consensusAddrs,
            uint64[] memory votingPowers,
            bytes[] memory voteAddrs
        ) = _batchCreateValidators(41);

        vm.startPrank(coinbase);
        validatorSet.updateValidatorSetV2(consensusAddrs, votingPowers, voteAddrs);

        for (uint256 i; i < 41; ++i) {
            validatorSet.deposit{ value: 1 ether }(consensusAddrs[i]);
        }
        vm.stopPrank();

        (operatorAddrs, consensusAddrs, votingPowers, voteAddrs) = _batchCreateValidators(41);
        vm.prank(coinbase);
        validatorSet.updateValidatorSetV2(consensusAddrs, votingPowers, voteAddrs);
    }

    function testDistributeFinalityReward() public {
        address[] memory addrs = new address[](20);
        uint256[] memory weights = new uint256[](20);
        address[] memory vals = validatorSet.getValidators();
        for (uint256 i; i < 10; ++i) {
            addrs[i] = vals[i];
            weights[i] = 1;
        }

        for (uint256 i = 10; i < 20; ++i) {
            vals[i] = _getNextUserAddress();
            weights[i] = 1;
        }

        // failed case
        uint256 ceil = validatorSet.MAX_SYSTEM_REWARD_BALANCE();
        vm.deal(address(systemReward), ceil - 1);
        vm.expectRevert(bytes("the message sender must be the block producer"));
        validatorSet.distributeFinalityReward(addrs, weights);

        vm.startPrank(coinbase);
        validatorSet.distributeFinalityReward(addrs, weights);
        vm.expectRevert(bytes("can not do this twice in one block"));
        validatorSet.distributeFinalityReward(addrs, weights);

        // success case
        // balanceOfSystemReward > MAX_SYSTEM_REWARD_BALANCE
        uint256 reward = 1 ether;
        vm.deal(address(systemReward), ceil + reward);
        vm.roll(block.number + 1);

        uint256 expectReward = reward / 20;
        vm.expectEmit(true, false, false, true, address(validatorSet));
        emit finalityRewardDeposit(addrs[0], expectReward);
        vm.expectEmit(true, false, false, true, address(validatorSet));
        emit finalityRewardDeposit(addrs[9], expectReward);
        vm.expectEmit(true, false, false, true, address(validatorSet));
        emit deprecatedFinalityRewardDeposit(addrs[10], expectReward);
        vm.expectEmit(true, false, false, true, address(validatorSet));
        emit deprecatedFinalityRewardDeposit(addrs[19], expectReward);
        validatorSet.distributeFinalityReward(addrs, weights);
        assertEq(address(systemReward).balance, ceil);

        // cannot exceed MAX_REWARDS
        uint256 cap = systemReward.MAX_REWARDS();
        vm.deal(address(systemReward), ceil + cap * 2);
        vm.roll(block.number + 1);

        expectReward = cap / 20;
        vm.expectEmit(true, false, false, true, address(validatorSet));
        emit finalityRewardDeposit(addrs[0], expectReward);
        vm.expectEmit(true, false, false, true, address(validatorSet));
        emit finalityRewardDeposit(addrs[9], expectReward);
        vm.expectEmit(true, false, false, true, address(validatorSet));
        emit deprecatedFinalityRewardDeposit(addrs[10], expectReward);
        vm.expectEmit(true, false, false, true, address(validatorSet));
        emit deprecatedFinalityRewardDeposit(addrs[19], expectReward);
        validatorSet.distributeFinalityReward(addrs, weights);
        assertEq(address(systemReward).balance, ceil + cap);

        vm.stopPrank();
    }

    function _calcIncoming(uint256 value) internal view returns (uint256 incoming) {
        uint256 turnLength = validatorSet.getTurnLength();
        uint256 systemRewardAntiMEVRatio = validatorSet.systemRewardAntiMEVRatio();
        uint256 systemRewardRatio = systemRewardBaseRatio;
        if (turnLength > 1 && systemRewardAntiMEVRatio > 0) {
            systemRewardRatio += systemRewardAntiMEVRatio * (block.number % turnLength) / (turnLength - 1);
        }
        uint256 toSystemReward = (value * systemRewardRatio) / systemRewardRatioScale;
        uint256 toBurn = (value * burnRatio) / burnRatioScale;
        incoming = value - toSystemReward - toBurn;
    }
}
