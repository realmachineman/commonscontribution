// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/// Local testnet prototype. Meter attestations must be validated off chain.
contract ContributionToken is ERC20, AccessControl {
 bytes32 public constant MINTER_ROLE=keccak256("MINTER_ROLE");
 constructor(address admin) ERC20("Commons Contribution","CONTRIB") {_grantRole(DEFAULT_ADMIN_ROLE,admin);}
 function mint(address user,uint256 amount) external onlyRole(MINTER_ROLE){_mint(user,amount);}
}
contract ResourceTracker is ERC1155, AccessControl {
 bytes32 public constant STEWARD_ROLE=keccak256("STEWARD_ROLE");
 ContributionToken public immutable token;uint256 public nextBatch=1;
 event HarvestLogged(uint256 indexed batch,address indexed contributor,string cropType,uint256 quantity,uint256 harvestTime);
 event WaterDispensed(address indexed user,uint256 liters);
 event KineticRecorded(address indexed user,uint256 kwh);
 event LaborRecorded(address indexed user,uint256 minutesWorked,bytes32 indexed evidence);
 mapping(bytes32=>bool) public evidenceUsed;
 constructor(address admin,ContributionToken credit) ERC1155("") {token=credit;_grantRole(DEFAULT_ADMIN_ROLE,admin);_grantRole(STEWARD_ROLE,admin);}
 function logHarvest(string calldata cropType,uint256 quantity,uint256 harvestTime) external onlyRole(STEWARD_ROLE){require(quantity>0&&harvestTime<=block.timestamp,"Invalid harvest");uint256 batch=nextBatch++;_mint(msg.sender,batch,quantity,"");emit HarvestLogged(batch,msg.sender,cropType,quantity,harvestTime);}
 function dispenseWater(address user,uint256 liters) external onlyRole(STEWARD_ROLE){require(user!=address(0)&&liters>0,"Invalid allocation");_mint(user,nextBatch++,liters,"");emit WaterDispensed(user,liters);}
 function recordKineticEnergy(address user,uint256 kwh) external onlyRole(STEWARD_ROLE){require(kwh>0,"No energy");token.mint(user,kwh*1 ether);emit KineticRecorded(user,kwh);}
 function recordLabor(address user,uint256 minutesWorked,bytes32 evidence) external onlyRole(STEWARD_ROLE){require(minutesWorked>0&&!evidenceUsed[evidence],"Invalid evidence");evidenceUsed[evidence]=true;token.mint(user,minutesWorked*15 ether/60);emit LaborRecorded(user,minutesWorked,evidence);}
 function supportsInterface(bytes4 interfaceId) public view override(ERC1155,AccessControl) returns(bool){return super.supportsInterface(interfaceId);}
}
