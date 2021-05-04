#pragma once
#include "CTRPluginFramework.hpp"
#include "Minibson.hpp" // https://github.com/cyberguijarro/minibson

namespace CTRPluginFramework {
	class NetHandler
	{
	public:
		class Session
		{
		public:
			enum class Status
			{
				IDLE,
				PROCESSING,
				SUCCESS,
				FAILURE
			};

			Session(const std::string& url);
			~Session();
			void SetData(const minibson::document& data);
			void setFinishedCallback(bool(*callback)(void*), void* arg = nullptr);
			void ClearInputData();
			void Cleanup();
			const minibson::document& GetData();
			void Start();
			void Wait();
			void WaitTimeout(const Time& time);
			Status GetStatus();
			bool HasFinished();
			Result lastRes;
			static const minibson::document defaultDoc;
			LightEvent waitEvent;
			static std::vector<Session*> pendingSessions;

			static void Initialize();
			static void Terminate();
			static ThreadEx* sessionThread;
		private:
			void Init();
			void Reset();
			const std::string& remoteUrl;
			u8* rawbsondata;
			u32 rawbsonsize;
			Status status;
			bool isFinished;
			minibson::encdocument* outputData;
			bool(*finishedCallback)(void*);
			void* finishedCallbackData;
			
			void bsontopayload(const minibson::document& data);
			s32 payloadtobson(u8* data, u32 size);
			static void sessionFunc(void* arg);
			
			static Mutex pendingSessionsMutex;
			static LightEvent threadEvent;
			static bool runThread;
		};

		class RequestHandler
		{
		public:
			enum class RequestType
			{
				BETA_VER,
				PUT_GENERAL_STATS,
				LOGIN,
				LOGOUT,
				ONLINE_SEARCH,
				ONLINE_PREPARING,
				ONLINE_RACING,
				ONLINE_WATCHING,
				ONLINE_LEAVEROOM,
				RELOGIN,
				HEARTBEAT
			};
			RequestHandler();

			template <class Tin>
			void AddRequest(RequestType type, const Tin& value);
			void AddRequest(RequestType type, const minibson::document& value);

			void Cleanup();
			void Start(bool startSession = true);
			void Wait();
			void WaitTimeout(const Time& time);
			Result GetLastResult();
			Session::Status GetStatus();
			bool HasFinished();
			void SetFinishedCallback(bool(*callback)(RequestHandler*));

			template <class Tout>
			int GetResult(RequestType type, Tout* value);
			int GetResult(RequestType type, minibson::document* value);
			bool Contains(RequestType type);

		private:
			Session session;
			minibson::document doc;
			std::vector<RequestType> addedRequests;

			static const char* reqStr[];
		};

		static const std::string mainServerURL;

		static u64 GetConsoleUniqueHash();
		static void InitColsoleUniqueHash();
		static void SetHttpcStolenMemory(u32* addr);
		static u32* GetHttpcStolenMemory();

	private:
		static u64 ConsoleUniqueHash;
		static u32* HttpcStolenMemory;
	};
}