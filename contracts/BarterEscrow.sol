// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
/// Native-token escrow for testnet demonstrations, not audited for real funds.
contract BarterEscrow is ReentrancyGuard {
 struct Trade{address buyer;address seller;uint256 value;uint256 deadline;bool accepted;bool buyerDone;bool sellerDone;bool closed;}
 mapping(uint256=>Trade) public trades;uint256 public nextId;
 event Opened(uint256 indexed id,address indexed buyer,address indexed seller,uint256 amount,uint256 deadline,bytes32 termsHash);
 event Accepted(uint256 indexed id);event Completed(uint256 indexed id);event Refunded(uint256 indexed id);
 function open(address seller,uint256 deadline,bytes32 termsHash) external payable returns(uint256 id){require(seller!=address(0)&&seller!=msg.sender&&msg.value>0&&deadline>block.timestamp,"Invalid offer");id=nextId++;trades[id]=Trade(msg.sender,seller,msg.value,deadline,false,false,false,false);emit Opened(id,msg.sender,seller,msg.value,deadline,termsHash);}
 function accept(uint256 id) external {Trade storage t=trades[id];require(msg.sender==t.seller&&!t.closed&&!t.accepted&&block.timestamp<t.deadline,"Unavailable");t.accepted=true;emit Accepted(id);}
 function confirm(uint256 id) external nonReentrant{Trade storage t=trades[id];require(t.accepted&&!t.closed,"Unavailable");require(msg.sender==t.buyer||msg.sender==t.seller,"Not participant");if(msg.sender==t.buyer)t.buyerDone=true;else t.sellerDone=true;if(t.buyerDone&&t.sellerDone){t.closed=true;(bool ok,)=t.seller.call{value:t.value}("");require(ok,"Transfer failed");emit Completed(id);}}
 function cancelUnaccepted(uint256 id) external nonReentrant{Trade storage t=trades[id];require(msg.sender==t.buyer&&!t.accepted&&!t.closed,"Unavailable");_refund(id,t);}
 function refundExpired(uint256 id) external nonReentrant{Trade storage t=trades[id];require(msg.sender==t.buyer&&!t.closed&&block.timestamp>t.deadline,"Unavailable");require(!t.buyerDone,"Buyer confirmed delivery");_refund(id,t);}
 function _refund(uint256 id,Trade storage t) internal {t.closed=true;(bool ok,)=t.buyer.call{value:t.value}("");require(ok,"Refund failed");emit Refunded(id);}
}
