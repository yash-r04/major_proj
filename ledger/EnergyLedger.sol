// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract EnergyLedger {
    struct Trade {
        string sellerId;
        string buyerId;
        uint256 volumeKw;  // Stored scaled by 100 (e.g. 1.50 kW -> 150)
        uint256 price;     // Stored scaled by 100 (e.g. 4.25 INR -> 425)
        uint256 timestamp;
    }

    Trade[] public trades;
    address public operator;

    event TradeRecorded(string sellerId, string buyerId, uint256 volumeKw, uint256 price, uint256 timestamp);

    constructor() {
        operator = msg.sender;
    }

    function recordTrade(string memory sellerId, string memory buyerId, uint256 volumeKw, uint256 price) public {
        trades.push(Trade(sellerId, buyerId, volumeKw, price, block.timestamp));
        emit TradeRecorded(sellerId, buyerId, volumeKw, price, block.timestamp);
    }

    function getTradeCount() public view returns (uint256) {
        return trades.length;
    }
}