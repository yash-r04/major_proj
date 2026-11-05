// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Records cleared P2P trades and settlement penalties.
/// Only the operator (deployer) may write. Raw meter data never goes on-chain.
contract EnergyLedger {
    struct Trade {
        string sellerId;
        string buyerId;
        uint256 volumeWh;     // watt-hours (1.5 kWh -> 1500)
        uint256 pricePaise;   // paise per kWh (Rs 4.25 -> 425)
        uint256 slot;
        uint256 timestamp;
    }

    Trade[] public trades;
    address public operator;

    event TradeRecorded(string sellerId, string buyerId, uint256 volumeWh, uint256 pricePaise, uint256 slot, uint256 timestamp);
    event PenaltyRecorded(string deviceId, uint256 slot, uint256 timestamp);

    modifier onlyOperator() {
        require(msg.sender == operator, "only operator");
        _;
    }

    constructor() {
        operator = msg.sender;
    }

    function recordTrade(
        string memory sellerId,
        string memory buyerId,
        uint256 volumeWh,
        uint256 pricePaise,
        uint256 slot
    ) public onlyOperator {
        trades.push(Trade(sellerId, buyerId, volumeWh, pricePaise, slot, block.timestamp));
        emit TradeRecorded(sellerId, buyerId, volumeWh, pricePaise, slot, block.timestamp);
    }

    function recordPenalty(string memory deviceId, uint256 slot) public onlyOperator {
        emit PenaltyRecorded(deviceId, slot, block.timestamp);
    }

    function getTradeCount() public view returns (uint256) {
        return trades.length;
    }
}
