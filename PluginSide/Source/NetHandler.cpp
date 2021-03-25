#include "NetHandler.hpp"

namespace CTRPluginFramework {
	std::vector<NetHandler::Session*> NetHandler::Session::pendingSessions;
	Mutex NetHandler::Session::pendingSessionsMutex{};
	ThreadEx* NetHandler::Session::sessionThread;
	LightEvent NetHandler::Session::threadEvent;
	bool NetHandler::Session::runThread = false;

	u32* NetHandler::HttpcStolenMemory = nullptr;
	const minibson::document NetHandler::Session::defaultDoc;
	const std::string NetHandler::mainServerURL = ""; // URL hidden in open source version, for obvious reasons.

	u64 NetHandler::ConsoleUniqueHash = 0;

	const char* NetHandler::RequestHandler::reqStr[] = {
		"req_betaver",
		"put_generalstats",
		"req_login",
		"req_logout",
		"put_onlsearch",
		"put_onlprepare",
		"put_onlrace",
		"put_onlwatch",
		"put_onlleaveroom",
		"req_login", // Intended, do relogin
		"put_hrtbt"
	};

	NetHandler::Session::Session(const std::string& url) : remoteUrl(url)
	{
		LightEvent_Init(&waitEvent, ResetType::RESET_STICKY);
		finishedCallback = nullptr;
		finishedCallbackData = nullptr;
		isFinished = true;
		Init();
	}

	void NetHandler::Session::Initialize()
	{
		runThread = true;
		LightEvent_Init(&threadEvent, RESET_STICKY);
		sessionThread = new ThreadEx(sessionFunc, 0x800, 0x20, System::IsNew3DS() ? 2 : 1);
		sessionThread->Start(nullptr);
	}

	void NetHandler::Session::Terminate()
	{
		runThread = false;
		LightEvent_Signal(&threadEvent);
	}

	void NetHandler::Session::Init()
	{
		status = Status::IDLE;
		rawbsondata = nullptr;
		rawbsonsize = 0;
		lastRes = 0;
		outputData = nullptr;
	}

	NetHandler::Session::~Session()
	{
		Reset();
	}

	void NetHandler::Session::Reset()
	{
		if (status == Status::PROCESSING)
			Wait();
		status = Status::IDLE;
		ClearInputData();
		if (outputData)
			delete outputData;
		outputData = nullptr;
	}

	void NetHandler::Session::SetData(const minibson::document& data)
	{
		bsontopayload(data);
	}

	void NetHandler::Session::setFinishedCallback(bool(*callback)(void*), void* arg)
	{
		finishedCallback = callback;
		finishedCallbackData = arg;
	}

	void NetHandler::Session::ClearInputData()
	{
		if (rawbsondata)
			::operator delete(rawbsondata);
		rawbsondata = nullptr;
		rawbsonsize = 0;
	}

	void NetHandler::Session::Cleanup()
	{
		Reset();
		Init();
	}	

	const minibson::document& NetHandler::Session::GetData()
	{
		if (GetStatus() == Status::SUCCESS && outputData)
			return *outputData;
		else
			return defaultDoc;
	}

	void NetHandler::Session::Start()
	{
		Lock lock(pendingSessionsMutex);

		status = Status::PROCESSING;
		isFinished = false;
		pendingSessions.push_back(this);
		LightEvent_Clear(&waitEvent);

		LightEvent_Signal(&threadEvent);	
	}

	void NetHandler::Session::Wait()
	{
		LightEvent_Wait(&waitEvent);
	}

	void NetHandler::Session::WaitTimeout(const Time& time)
	{
		LightEvent_WaitTimeout(&waitEvent, time.AsMicroseconds() * 1000);
	}

	NetHandler::Session::Status NetHandler::Session::GetStatus()
	{
		Lock lock(pendingSessionsMutex);
		return status;
	}

	bool NetHandler::Session::HasFinished()
	{
		return isFinished;
	}

	void NetHandler::Session::bsontopayload(const minibson::document& data)
	{
		if (rawbsondata)
			::operator delete(rawbsondata);

		minibson::encdocument encData(data);

		encData.set("_CID", (u64)NetHandler::GetConsoleUniqueHash());

		rawbsonsize = encData.get_serialized_size();
		rawbsondata = (u8*)::operator new(rawbsonsize);
		
		encData.serialize(rawbsondata, rawbsonsize);
	}

	s32 NetHandler::Session::payloadtobson(u8* data, u32 size)
	{
		if (outputData)
			delete outputData;
		outputData = new minibson::encdocument(data, size);
		if (!outputData->valid || outputData->get<int>("res", -1) < 0 || outputData->get_numerical("_CID", 0LL) != GetConsoleUniqueHash()) {
			delete outputData;
			outputData = nullptr;
			return -1;
		}
		return 0;
	}

	void NetHandler::Session::sessionFunc(void* arg)
	{		
		Session* currS;
		u32				downSize = 0;
		u32             responseCode = 0;
		u32             totalSize = 0, bytesRead = 0;
		Result          res = 0, initres = 0;
		httpcPatchContext    context;
		char            userAgent[128];
		u8* buf = NULL;
		bool repeatSession = false;

		while (true) {
			LightEvent_Wait(&threadEvent);
			LightEvent_Clear(&threadEvent);

			if (!runThread)
				break;

			// Normally, httpcInit tries to allocate a memory block automatically,
			// however, the plugin memory is not placed in the process heap, as it's
			// used by the game. That's why we have to steal memory from the game
			// and modify httpc code to use the memory block we pass as argument.
			// For normal homebrew apps you can just use unmodified httpc instead. 
			initres = httpcPatchInit((u32)NetHandler::GetHttpcStolenMemory(), 0x2000);

			while (R_SUCCEEDED(initres))
			{
				buf = NULL; downSize = 0; responseCode = 0; totalSize = 0; bytesRead = 0;
				if (!repeatSession)
				{
					Lock lock(pendingSessionsMutex);
					if (pendingSessions.empty())
						break;
					currS = pendingSessions.back();
					pendingSessions.pop_back();
				}

				if (currS->rawbsondata == nullptr || currS->rawbsonsize == 0) {
					repeatSession = false;
					currS->status = Status::FAILURE;
					currS->lastRes = -1;
					if (currS->finishedCallback)
						repeatSession = currS->finishedCallback(currS->finishedCallbackData);
					if (!repeatSession) currS->isFinished = true;
					if (!repeatSession) LightEvent_Signal(&currS->waitEvent);
					continue;
				}

				if (R_SUCCEEDED(res = httpcPatchOpenContext(&context, HTTPCPATCH_METHOD_POST, currS->remoteUrl.c_str(), 0)))
				{
					snprintf(userAgent, sizeof(userAgent), "Mozilla/5.0");
					if (R_SUCCEEDED(res = httpcPatchSetSSLOpt(&context, SSLCOPT_DisableVerify))
						&& R_SUCCEEDED(res = httpcPatchSetKeepAlive(&context, HTTPCPATCH_KEEPALIVE_DISABLED))
						&& R_SUCCEEDED(res = httpcPatchAddRequestHeaderField(&context, "User-Agent", userAgent))
						&& R_SUCCEEDED(res = httpcPatchAddRequestHeaderField(&context, "Content-Type", "application/octet-stream"))
						&& R_SUCCEEDED(res = httpcPatchAddPostDataRaw(&context, (u32*)currS->rawbsondata, currS->rawbsonsize))
						&& R_SUCCEEDED(res = httpcPatchBeginRequest(&context))
						&& R_SUCCEEDED(res = httpcPatchGetResponseStatusCodeTimeout(&context, &responseCode, 10ULL * 1000ULL * 1000ULL * 1000ULL))
						&& R_SUCCEEDED(res = httpcPatchGetDownloadSizeState(&context, NULL, &totalSize)))
					{
						if (responseCode == 200)
						{
							if (totalSize == 0 || totalSize > 0x2000) {
								res = -4;
							}
							else {
								buf = (u8*)::operator new(totalSize);
								res = httpcPatchDownloadData(&context, buf, totalSize, &bytesRead);
								if (bytesRead != totalSize)
									res = -5;
							}
						}
						else res = -2;
					}
					httpcPatchCloseContext(&context);
				}

				currS->ClearInputData();

				if (R_SUCCEEDED(res))
					res = currS->payloadtobson(buf, totalSize);

				if (buf)
					::operator delete(buf);

				currS->lastRes = res;

				if (R_SUCCEEDED(res))
					currS->status = Status::SUCCESS;
				else
					currS->status = Status::FAILURE;

				repeatSession = false;
				if (currS->finishedCallback)
					repeatSession = currS->finishedCallback(currS->finishedCallbackData);

				if (!repeatSession) currS->isFinished = true;
				if (!repeatSession) LightEvent_Signal(&currS->waitEvent);
			}
			if (R_SUCCEEDED(initres)) httpcPatchExit();
		}
	}

	u64 NetHandler::GetConsoleUniqueHash()
	{
		return ConsoleUniqueHash;
	}

	void NetHandler::InitColsoleUniqueHash()
	{
		// This function has been stubbed in the open source version.
		// You can generate any console unique data here to tell multiple users appart.
		ConsoleUniqueHash = 1;
	}

	NetHandler::RequestHandler::RequestHandler() : session(NetHandler::mainServerURL) { }

	template<class Tin>
	void NetHandler::RequestHandler::AddRequest(RequestType type, const Tin& value)
	{
		minibson::document reqDoc;
		reqDoc.set<Tin>("value", value);

		doc.set(reqStr[(int)type], reqDoc);
		addedRequests.push_back(type);
	}
	template void NetHandler::RequestHandler::AddRequest<int>(RequestType type, const int& value);

	void NetHandler::RequestHandler::AddRequest(RequestType type, const minibson::document& value)
	{
		minibson::document reqDoc;
		reqDoc.set("value", value);

		doc.set(reqStr[(int)type], reqDoc);
		addedRequests.push_back(type);
	}

	void NetHandler::RequestHandler::Cleanup()
	{
		session.Cleanup();
		doc.clear();
		addedRequests.clear();
	}

	void NetHandler::RequestHandler::Start(bool startSession)
	{
		session.SetData(doc);
		if (startSession) session.Start();
	}

	void NetHandler::RequestHandler::Wait()
	{
		session.Wait();
	}

	void NetHandler::RequestHandler::WaitTimeout(const Time& time)
	{
		session.WaitTimeout(time);
	}

	Result NetHandler::RequestHandler::GetLastResult()
	{
		return session.lastRes;
	}

	NetHandler::Session::Status NetHandler::RequestHandler::GetStatus()
	{
		return session.GetStatus();
	}

	bool NetHandler::RequestHandler::HasFinished()
	{
		return session.HasFinished();
	}

	void NetHandler::RequestHandler::SetFinishedCallback(bool(*callback)(RequestHandler*))
	{
		session.setFinishedCallback(reinterpret_cast<bool(*)(void*)>(callback), this);
	}

	template<class Tout>
	int NetHandler::RequestHandler::GetResult(RequestType type, Tout* value)
	{
		int res = -1;
		if (session.GetStatus() != Session::Status::SUCCESS)
			return res;

		const minibson::document& out = session.GetData();

		if (out.contains<minibson::document>(reqStr[(int)type])) {
			minibson::document defDoc;
			const minibson::document& reply = out.get(reqStr[(int)type], defDoc);
			res = reply.get<int>("res", -1);
			if (res >= 0)
				*value = reply.get<Tout>("value", *value);
		}

		return res;
	}
	template int NetHandler::RequestHandler::GetResult<int>(RequestType type, int* value);

	int NetHandler::RequestHandler::GetResult(RequestType type, minibson::document* value)
	{
		int res = -1;
		if (session.GetStatus() != Session::Status::SUCCESS)
			return res;

		const minibson::document& out = session.GetData();

		if (out.contains<minibson::document>(reqStr[(int)type])) {
			minibson::document defDoc;
			const minibson::document& reply = out.get(reqStr[(int)type], defDoc);
			res = reply.get<int>("res", -1);
			if (res >= 0)
				*value = reply.get("value", *value);
		}

		return res;
	}

	bool NetHandler::RequestHandler::Contains(RequestType type)
	{
		return std::find(addedRequests.begin(), addedRequests.end(), type) != addedRequests.end();
	}

	void NetHandler::SetHttpcStolenMemory(u32* addr)
	{
		HttpcStolenMemory = addr;
	}

	u32* NetHandler::GetHttpcStolenMemory()
	{
		return HttpcStolenMemory;
	}
}
