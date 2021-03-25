#include "Net.hpp"
// Other CTGP-7 plugin specific includes are placed here.

namespace CTRPluginFramework {
	NetHandler::RequestHandler Net::netRequests;
	Net::CTWWLoginStatus Net::lastLoginStatus = Net::CTWWLoginStatus::NOTLOGGED;
	Net::OnlineStateMachine Net::currState = Net::OnlineStateMachine::OFFLINE;
	std::string Net::lastServerMessage;
	u32 Net::currLoginSeed = 0;
	u64 Net::currLoginToken = 0;

	Net::CTWWLoginStatus Net::GetLoginStatus()
	{
		return lastLoginStatus;
	}

	const std::string& Net::GetServerMessage()
	{
		return lastServerMessage;
	}

	void Net::AcknowledgeMessage()
	{
		if (lastLoginStatus == CTWWLoginStatus::MESSAGE)
			lastLoginStatus = CTWWLoginStatus::SUCCESS;
	}
#ifdef BETA_BUILD
	NetHandler::RequestHandler Net::betaRequests;
	Net::BetaState Net::betaState = Net::BetaState::NONE;
	void Net::StartBetaRequest()
	{
		if (betaState != BetaState::NONE)
			return;
		betaState = BetaState::GETTING;
		betaRequests.SetFinishedCallback(OnBetaRequestFinishCallback);
		betaRequests.AddRequest<int>(NetHandler::RequestHandler::RequestType::BETA_VER, lastBetaVersion);
		betaRequests.Start();
	}

	Net::BetaState Net::GetBetaState()
	{
		return betaState;
	}

	bool Net::OnBetaRequestFinishCallback(NetHandler::RequestHandler* req)
	{
		int def = 0;
		int res = req->GetResult(NetHandler::RequestHandler::RequestType::BETA_VER, &def);
		if (res == 0)
			betaState = BetaState::YES;
		else
			betaState = BetaState::NO;
		req->Cleanup();
		return false;
	}
#endif

	bool Net::OnRequestFinishCallback(NetHandler::RequestHandler* req) {
		int res = -1;
		minibson::document reqDoc;
		if (req->Contains(NetHandler::RequestHandler::RequestType::LOGIN)) {
			res = req->GetResult(NetHandler::RequestHandler::RequestType::LOGIN, &reqDoc);
			if (res < 0)
				lastLoginStatus = CTWWLoginStatus::FAILED;
			else {
				CTWWLoginStatus stat = static_cast<CTWWLoginStatus>(res);
				if (currLoginSeed != reqDoc.get<int>("seed", currLoginSeed | 0x80000000))
					stat = CTWWLoginStatus::FAILED;
				currLoginToken = reqDoc.get_numerical("token", 0);
				switch (stat)
				{
				case CTWWLoginStatus::NOTLOGGED:
				case CTWWLoginStatus::PROCESSING:
				case CTWWLoginStatus::FAILED:
					stat = CTWWLoginStatus::FAILED;
					break;
				case CTWWLoginStatus::SUCCESS:
				case CTWWLoginStatus::VERMISMATCH:
					break;
				case CTWWLoginStatus::MESSAGE:
					lastServerMessage = reqDoc.get("loginMessage", "Failed to get\nmessage.");
					break;
				case CTWWLoginStatus::MESSAGEKICK:
					lastServerMessage = reqDoc.get("loginMessage", "Failed to get\nkick message");
					break;
				default:
					break;
				}

				lastLoginStatus = stat;
			}
		}
		else if (req->Contains(NetHandler::RequestHandler::RequestType::ONLINE_SEARCH)) {
			res = req->GetResult(NetHandler::RequestHandler::RequestType::ONLINE_SEARCH, &reqDoc);
			if (static_cast<CTWWLoginStatus>(res) != CTWWLoginStatus::SUCCESS) {
				if (static_cast<CTWWLoginStatus>(res) == CTWWLoginStatus::NOTLOGGED)
				{
					currLoginSeed = Utils::Random() & ~0x80000000;
					minibson::document newDoc;
					PlayerNameMode currPlayerNameMode = (PlayerNameMode)SaveHandler::saveData.serverDisplayNameMode;
					char miiName[sizeof(MarioKartFramework::SavePlayerData::miiData.name)];
					memset(miiName, 0, sizeof(miiName));
					MarioKartFramework::SavePlayerData sv;
					MarioKartFramework::getMyPlayerData(&sv);
					u32 playerNamePtr = (u32)sv.miiData.name;
					utf16_to_utf8((u8*)miiName, (u16*)playerNamePtr, sizeof(miiName) - 1);
					newDoc.set<int>("seed", currLoginSeed);
					newDoc.set<int>("nameMode", (int)currPlayerNameMode);
					newDoc.set("miiName", (const char*)miiName);
					newDoc.set<bool>("reLogin", true);
					if (currPlayerNameMode == PlayerNameMode::SHOW || currPlayerNameMode == PlayerNameMode::CUSTOM) {
						if (sv.miiData.flags.profanity) {
							newDoc.set<int>("nameMode", (int)PlayerNameMode::HIDDEN);
						}
						else {
							if (currPlayerNameMode == PlayerNameMode::SHOW)
								newDoc.set("nameValue", (const char*)miiName);
							else if (currPlayerNameMode == PlayerNameMode::CUSTOM)
								newDoc.set("nameValue", (std::string(SaveHandler::saveData.serverDisplayCustomName) + " [" + miiName + "]").c_str());
						}
					}
					newDoc.set<int>("localVer", lastOnlineVersion);
					req->Cleanup();
					req->AddRequest(NetHandler::RequestHandler::RequestType::RELOGIN, newDoc);
					req->Start(false);
					return true;
				}
				else
					MarioKartFramework::dialogBlackOut();
			}
		}
		else if (req->Contains(NetHandler::RequestHandler::RequestType::ONLINE_PREPARING)) {
			res = req->GetResult(NetHandler::RequestHandler::RequestType::ONLINE_PREPARING, &reqDoc);
			if (static_cast<CTWWLoginStatus>(res) != CTWWLoginStatus::SUCCESS)
			{
				if (static_cast<CTWWLoginStatus>(res) == CTWWLoginStatus::MESSAGEKICK) {
					MarioKartFramework::dialogBlackOut(reqDoc.get("loginMessage", "Failed to get\nkick message"));
				}
				else if (static_cast<CTWWLoginStatus>(res) == CTWWLoginStatus::VERMISMATCH) {
					MarioKartFramework::dialogBlackOut(LANG_NOTE("update_check"));
				} 
				else {
					MarioKartFramework::dialogBlackOut();
				}
			}
				
		}
		else if (req->Contains(NetHandler::RequestHandler::RequestType::ONLINE_RACING)) {
			res = req->GetResult(NetHandler::RequestHandler::RequestType::ONLINE_RACING, &reqDoc);
			if (static_cast<CTWWLoginStatus>(res) != CTWWLoginStatus::SUCCESS)
				MarioKartFramework::dialogBlackOut();
		}
		else if (req->Contains(NetHandler::RequestHandler::RequestType::ONLINE_WATCHING)) {
			res = req->GetResult(NetHandler::RequestHandler::RequestType::ONLINE_WATCHING, &reqDoc);
			if (static_cast<CTWWLoginStatus>(res) != CTWWLoginStatus::SUCCESS)
				MarioKartFramework::dialogBlackOut();
		}
		else if (req->Contains(NetHandler::RequestHandler::RequestType::RELOGIN)) {
			res = req->GetResult(NetHandler::RequestHandler::RequestType::RELOGIN, &reqDoc);
			if (static_cast<CTWWLoginStatus>(res) != CTWWLoginStatus::SUCCESS) {
				MarioKartFramework::dialogBlackOut();
			}
			else {
				currLoginToken = reqDoc.get_numerical("token", 0);
				if (MarioKartFramework::currGatheringID) {
					minibson::document newDoc;
					newDoc.set<u64>("token", currLoginToken);
					newDoc.set<u64>("gatherID", MarioKartFramework::currGatheringID);
					newDoc.set<int>("gameMode", (g_getCTModeVal == CTMode::ONLINE_CTWW) ? 0 : 1);
					req->Cleanup();
					req->AddRequest(NetHandler::RequestHandler::RequestType::ONLINE_SEARCH, newDoc);
					req->Start(false);
					return true;
				}					
			}
		}
		req->Cleanup();
		return false;
	}

	void Net::UpdateOnlineStateMahine(OnlineStateMachine mode, u32 info)
	{
		if (mode == currState)
			return;
		
		WaitOnlineStateMachine();

		if (currState == OnlineStateMachine::OFFLINE && mode == OnlineStateMachine::IDLE) // Login
		{
			currLoginSeed = Utils::Random() & ~0x80000000;
			minibson::document loginDoc;
			PlayerNameMode currPlayerNameMode = (PlayerNameMode)SaveHandler::saveData.serverDisplayNameMode;
			char miiName[sizeof(MarioKartFramework::SavePlayerData::miiData.name)];
			memset(miiName, 0, sizeof(miiName));
			MarioKartFramework::SavePlayerData sv;
			MarioKartFramework::getMyPlayerData(&sv);
			u32 playerNamePtr = (u32)sv.miiData.name;
			utf16_to_utf8((u8*)miiName, (u16*)playerNamePtr, sizeof(miiName) - 1);
			loginDoc.set<int>("seed", currLoginSeed);
			loginDoc.set<int>("nameMode", (int)currPlayerNameMode);
			loginDoc.set("miiName", (const char*)miiName);
			loginDoc.set<bool>("reLogin", false);
			if (currPlayerNameMode == PlayerNameMode::SHOW || currPlayerNameMode == PlayerNameMode::CUSTOM) {
				if (sv.miiData.flags.profanity) {
					loginDoc.set<int>("nameMode", (int)PlayerNameMode::HIDDEN);
				}
				else {
					if (currPlayerNameMode == PlayerNameMode::SHOW)
						loginDoc.set("nameValue", (const char*)miiName);
					else if (currPlayerNameMode == PlayerNameMode::CUSTOM)
						loginDoc.set("nameValue", (std::string(SaveHandler::saveData.serverDisplayCustomName) + " [" + miiName + "]").c_str());
				}
			}
			
			loginDoc.set<int>("localVer", lastOnlineVersion);
			lastLoginStatus = CTWWLoginStatus::PROCESSING;
			netRequests.AddRequest(NetHandler::RequestHandler::RequestType::LOGIN, loginDoc);
			netRequests.Start();
		}
		else if (mode == OnlineStateMachine::SEARCHING) { // Joining room
			if (g_getCTModeVal == CTMode::ONLINE_CTWW || g_getCTModeVal == CTMode::ONLINE_CTWW_CD) {
				minibson::document reqDoc;
				reqDoc.set<u64>("token", currLoginToken);
				reqDoc.set<u64>("gatherID", MarioKartFramework::currGatheringID);
				reqDoc.set<int>("gameMode", (g_getCTModeVal == CTMode::ONLINE_CTWW) ? 0 : 1);
				netRequests.AddRequest(NetHandler::RequestHandler::RequestType::ONLINE_SEARCH, reqDoc);
				netRequests.Start();
			}
		}
		else if (mode == OnlineStateMachine::PREPARING) { // Preparing room
			if (g_getCTModeVal == CTMode::ONLINE_CTWW || g_getCTModeVal == CTMode::ONLINE_CTWW_CD) {
				minibson::document reqDoc;
				reqDoc.set<u64>("token", currLoginToken);
				reqDoc.set<u64>("gatherID", MarioKartFramework::currGatheringID);
				reqDoc.set<bool>("imHost", MarioKartFramework::imRoomHost);
				reqDoc.set<int>("localVer", lastOnlineVersion);
				netRequests.AddRequest(NetHandler::RequestHandler::RequestType::ONLINE_PREPARING, reqDoc);
				netRequests.Start();
			}
			else if (g_getCTModeVal == CTMode::ONLINE_COM || g_getCTModeVal == CTMode::ONLINE_NOCTWW)
			{
				minibson::document reqDoc;
				reqDoc.set<u64>("token", currLoginToken);
				netRequests.AddRequest(NetHandler::RequestHandler::RequestType::HEARTBEAT, reqDoc);
				netRequests.Start();
			}
		}
		else if (mode == OnlineStateMachine::RACING) { // Room start racing
			if (g_getCTModeVal == CTMode::ONLINE_CTWW || g_getCTModeVal == CTMode::ONLINE_CTWW_CD) {
				minibson::document reqDoc;
				reqDoc.set<u64>("token", currLoginToken);
				reqDoc.set<u64>("gatherID", MarioKartFramework::currGatheringID);
				reqDoc.set("courseSzsID", globalNameData.entries[info].name);
				netRequests.AddRequest(NetHandler::RequestHandler::RequestType::ONLINE_RACING, reqDoc);
				netRequests.Start();
			}
		}
		else if (mode == OnlineStateMachine::WATCHING) { // Room start racing
			if (g_getCTModeVal == CTMode::ONLINE_CTWW || g_getCTModeVal == CTMode::ONLINE_CTWW_CD) {
				minibson::document reqDoc;
				reqDoc.set<u64>("token", currLoginToken);
				reqDoc.set<u64>("gatherID", MarioKartFramework::currGatheringID);
				netRequests.AddRequest(NetHandler::RequestHandler::RequestType::ONLINE_WATCHING, reqDoc);
				netRequests.Start();
			}
		}
		else if ((currState == OnlineStateMachine::SEARCHING || currState == OnlineStateMachine::PREPARING
			|| currState == OnlineStateMachine::WATCHING || currState == OnlineStateMachine::RACING) && mode == OnlineStateMachine::IDLE) {
			minibson::document reqDoc;
			reqDoc.set<u64>("token", currLoginToken);
			netRequests.AddRequest(NetHandler::RequestHandler::RequestType::ONLINE_LEAVEROOM, reqDoc);
			netRequests.Start();
		}
		else if (mode == OnlineStateMachine::OFFLINE) { // Logout
			netRequests.AddRequest(NetHandler::RequestHandler::RequestType::LOGOUT, 0);
			netRequests.Start();
		}

		currState = mode;		
	}
	void Net::WaitOnlineStateMachine()
	{
		while (!netRequests.HasFinished()) {
			netRequests.WaitTimeout(Seconds(0.1f));
		}
	}
	void Net::Initialize()
	{
		NetHandler::Session::Initialize();
		NetHandler::InitColsoleUniqueHash();
		netRequests.SetFinishedCallback(OnRequestFinishCallback);
	}
}

