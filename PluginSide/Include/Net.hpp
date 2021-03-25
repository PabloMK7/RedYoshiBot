#pragma once
#include "CTRPluginFramework.hpp"
#include "NetHandler.hpp"

#define xstr(s) str(s)
#define str(s) #s

namespace CTRPluginFramework {
	class Net
	{
	public:
		static constexpr u32 lastOnlineVersion = 17;
		static constexpr u32 lastBetaVersion = 5;

		enum class CTWWLoginStatus
		{
			SUCCESS = 0,
			NOTLOGGED = 1,
			PROCESSING = 2,
			FAILED = 3,
			VERMISMATCH = 4,
			MESSAGE = 5,
			MESSAGEKICK = 6,
		};
		static CTWWLoginStatus GetLoginStatus();
		static const std::string& GetServerMessage();
		static void AcknowledgeMessage();

#ifdef BETA_BUILD
		enum class BetaState
		{
			NONE = 0,
			GETTING = 1,
			YES = 2,
			NO = 3
		};
		static void StartBetaRequest();
		static BetaState GetBetaState();
#endif // BETA_BUILD

		enum class PlayerNameMode
		{
			HIDDEN = 0,
			SHOW = 1,
			CUSTOM = 2
		};

		enum class OnlineStateMachine
		{
			OFFLINE,
			IDLE,
			SEARCHING,
			WATCHING,
			PREPARING,
			RACING
		};

		static void UpdateOnlineStateMahine(OnlineStateMachine mode, u32 info = 0);
		static void WaitOnlineStateMachine();
		static void Initialize();

	private:
		static NetHandler::RequestHandler netRequests;
		static CTWWLoginStatus lastLoginStatus;
		static OnlineStateMachine currState;
		static std::string lastServerMessage;
		static u32 currLoginSeed;
		static u64 currLoginToken;

#ifdef BETA_BUILD
		static BetaState betaState;
		static NetHandler::RequestHandler betaRequests;
		static bool OnBetaRequestFinishCallback(NetHandler::RequestHandler* req);
#endif // 

		static bool OnRequestFinishCallback(NetHandler::RequestHandler* req);
	};
}