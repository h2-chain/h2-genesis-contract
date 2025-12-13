pragma solidity 0.6.4;

interface IValidatorSetV2 {
    function misdemeanor(address validator) external;
    function felony(address validator) external;
    function isCurrentValidator(address validator) external view returns (bool);

    function currentValidatorSetMap(address validator) external view returns (uint256);
    function numOfProtons() external view returns (uint256);
}
