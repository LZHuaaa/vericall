import React, { useEffect, useRef, useState } from 'react';
import AudioVisualizer from './components/AudioVisualizer';
import VictimPhone from './components/VictimPhone';
import { EvidenceCollector } from './services/evidenceCollector';
import {
    answerDemoCall,
    DemoCallDoc,
    endDemoCall,
    getWebClientId,
    listenToDemoCallState,
    startDemoCall,
    updateDemoTranscript
} from './services/firebaseService';
import { geminiService, SearchResult } from './services/geminiService';
import { pdrmSubmit } from './services/pdrmSubmit';
import { cleanupWebRTC, startWebRTCCall } from './services/webrtcService';
import { BotDetectionStatus, ConnectionState, LogMessage, ScamEvidence, ThreatAssessment } from './types';

// Icons
const PhoneIcon = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>;
const MobileIcon = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>;
const PhoneOffIcon = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-3.33-2.67m-2.67-3.34a19.79 19.79 0 0 1-3.07-8.63A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91" /><line x1="23" y1="1" x2="1" y2="23" /></svg>;
const SendIcon = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>;
const FileIcon = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>;
const BookIcon = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" /><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" /></svg>;
const AUTO_HANGUP_ENABLED = (import.meta.env.VITE_AUTO_HANGUP_ENABLED ?? 'true') === 'true';

const App: React.FC = () => {
    const [connectionState, setConnectionState] = useState<ConnectionState>(ConnectionState.DISCONNECTED);
    const [volume, setVolume] = useState(0);
    const [transcripts, setTranscripts] = useState<LogMessage[]>([]);
    const [textInput, setTextInput] = useState('');
    const [mode, setMode] = useState<'call' | 'text'>('call');
    const [scamLikelihood, setScamLikelihood] = useState(0);
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [toolLog, setToolLog] = useState<{ name: string, query: string, result: string } | null>(null);
    const [translationLog, setTranslationLog] = useState<{ lang: string, original: string, translated: string } | null>(null);
    const [teachInput, setTeachInput] = useState('');
    const [isTeachModalOpen, setIsTeachModalOpen] = useState(false);
    const [isReportOpen, setIsReportOpen] = useState(false);

    const [botStatus, setBotStatus] = useState<BotDetectionStatus | null>(null);
    const [evidence, setEvidence] = useState<ScamEvidence | null>(null);
    const [detectedPattern, setDetectedPattern] = useState<string | null>(null);

    const [liveUserTranscript, setLiveUserTranscript] = useState<string>('');
    const [liveAiTranscript, setLiveAiTranscript] = useState<string>('');

    // CALL DURATION FOR VICTIM PHONE
    const [callDuration, setCallDuration] = useState(0);
    const callTimerRef = useRef<NodeJS.Timeout | null>(null);

    // ANALYSIS RESULT FOR VICTIM PHONE
    const [analysisResult, setAnalysisResult] = useState<{
        wavlmScore: number;
        isScam: boolean;
        scamType: string;
        confidence: number;
    } | null>(null);
    const [threatAssessment, setThreatAssessment] = useState<ThreatAssessment | null>(null);

    // DEEPFAKE DETECTION STATE
    const [deepfakeDetected, setDeepfakeDetected] = useState(false);
    const [deepfakeScore, setDeepfakeScore] = useState(0);
    const [currentCallSessionId, setCurrentCallSessionId] = useState<string | null>(null);
    const [demoCallState, setDemoCallState] = useState<DemoCallDoc | null>(null);
    const [uiNotice, setUiNotice] = useState<string | null>(null);
    const [callActions, setCallActions] = useState<Array<{
        ts: number;
        action: string;
        reasons: string[];
    }>>([]);

    const scrollRef = useRef<HTMLDivElement>(null);
    const webClientIdRef = useRef<string>(getWebClientId());
    const hadGeminiConnectionRef = useRef<boolean>(false);

    useEffect(() => {
        geminiService.onConnectionStateChange = (state) => {
            if (state === ConnectionState.CONNECTED) {
                hadGeminiConnectionRef.current = true;
            }
            setConnectionState(state);
        };
        geminiService.onVolumeChange = setVolume;
        geminiService.onTranscript = (msg) => setTranscripts(prev => [...prev, msg]);
        geminiService.onPartialTranscript = (text, isUser) => {
            if (isUser) {
                setLiveUserTranscript(prev => prev + text);
            } else {
                setLiveAiTranscript(prev => prev + text);
            }
        };
        geminiService.onTurnComplete = (isUser) => {
            if (isUser) {
                setLiveUserTranscript('');
            } else {
                setLiveAiTranscript('');
            }
        };
        geminiService.onSearchResults = (results) => setSearchResults(prev => [...prev, ...results]);

        geminiService.onToolUse = (name, query, result) => {
            setToolLog({ name, query, result });
            setTimeout(() => setToolLog(null), 5000);
        };

        geminiService.onTranslation = (lang, original, translated) => {
            setTranslationLog({ lang, original, translated });
            setTimeout(() => setTranslationLog(null), 8000);
        };

        geminiService.onBotDetected = (status) => {
            if (status.isSuspicious) setBotStatus(status);
        };

        geminiService.onEvidenceReady = (report) => {
            console.log('🎯 App received evidence report:', report);
            console.log('   Has callRecording?', !!report.callRecording);
            console.log('   callRecording size:', report.callRecording?.size);

            setEvidence(report);
            setIsReportOpen(true);
        };

        geminiService.onScamPatternDetected = (pattern) => {
            setDetectedPattern(pattern);
            setTimeout(() => setDetectedPattern(null), 5000);
        };

        geminiService.onScamProbabilityChange = (prob) => {
            setScamLikelihood(prob);
        };

        geminiService.onThreatAssessment = (assessment: ThreatAssessment) => {
            setThreatAssessment(assessment);
            const prob = Math.round((assessment.risk_score || 0) * 100);
            setScamLikelihood(prob);

            const deepfakeSignal = assessment.signals?.find(signal => signal.name === 'deepfake');
            const scamTypeReason = assessment.reason_codes?.find(code => code.startsWith('llm_scam_type_'));
            const inferredScamType = scamTypeReason
                ? scamTypeReason.replace('llm_scam_type_', '')
                : assessment.risk_level;

            setAnalysisResult({
                wavlmScore: deepfakeSignal?.score ?? 0,
                isScam: assessment.risk_level === 'high' || assessment.risk_level === 'critical',
                scamType: inferredScamType,
                confidence: assessment.confidence ?? assessment.risk_score ?? 0
            });
        };

        geminiService.onCallAction = (event) => {
            setCallActions(prev => [{
                ts: Date.now(),
                action: event.action,
                reasons: event.reasonCodes || []
            }, ...prev].slice(0, 8));
        };

        // 🚨 WavLM Deepfake Detection Callback
        geminiService.onWavLMResult = (result) => {
            const confidence = result.confidence ?? 0;
            const activeSpeechRatio = result.activeSpeechRatio ?? 0;
            setDeepfakeDetected(result.isDeepfake && confidence >= 0.75 && activeSpeechRatio >= 0.25);
            setDeepfakeScore(result.score);
            console.log(`🎭 VictimPhone: Deepfake ${result.isDeepfake ? 'DETECTED!' : 'OK'} (${Math.round(result.score * 100)}%)`);
        };

        // 🔥 Sync transcript to Firebase for Flutter app to display
        geminiService.onTranscript = (msg) => {
            setTranscripts(prev => [...prev, msg]);
            // Also send to Firebase for Flutter
            updateDemoTranscript(msg.text, msg.sender === 'user').catch(console.error);
        };

        return () => geminiService.disconnect();
    }, []);

    useEffect(() => {
        const unsubscribe = listenToDemoCallState((state) => {
            setDemoCallState(state);
            const sessionId = (state?.sessionId || '').trim();
            if (sessionId) {
                setCurrentCallSessionId(sessionId);
            }
            if (typeof state?.scamProbability === 'number') {
                setScamLikelihood(Math.max(0, Math.min(100, Math.round(state.scamProbability))));
            }
            const summary = state?.threatSummary;
            if (summary) {
                setThreatAssessment({
                    risk_level: (summary.risk_level as any) || 'low',
                    risk_score: Number(summary.risk_score || 0),
                    confidence: Number(summary.confidence || 0),
                    reason_codes: Array.isArray(summary.reason_codes) ? summary.reason_codes : [],
                    recommended_actions: [],
                    evidence_items: [],
                    retrieval_status: summary.retrieval_status || 'unknown',
                    signals: [],
                    mode: (summary.mode as any) === 'degraded_local' ? 'degraded_local' : 'normal',
                    version: 'threat-v2',
                    call_action: (summary.call_action as any) || 'none',
                    call_action_reason_codes: Array.isArray(summary.call_action_reason_codes) ? summary.call_action_reason_codes : []
                });
            }
        });
        return () => unsubscribe();
    }, []);

    useEffect(() => {
        if (!uiNotice) return;
        const timer = setTimeout(() => setUiNotice(null), 2500);
        return () => clearTimeout(timer);
    }, [uiNotice]);

    const handleConnect = async () => {
        const liveState = (demoCallState?.state || 'idle') as string;
        const activeSessionId = (demoCallState?.sessionId || currentCallSessionId || '').trim();
        const inLiveCall = liveState === 'ringing' || liveState === 'connected';

        if (inLiveCall) {
            if (connectionState === ConnectionState.CONNECTED) {
                await geminiService.disconnect();
            }
            try {
                await endDemoCall(activeSessionId || undefined, ['manual_disconnect'], {
                    endedBy: 'web_client',
                    device: 'web',
                    clientId: webClientIdRef.current
                });
            } catch (error) {
                setUiNotice((error as Error).message || 'Unable to end call from this device.');
            }
            return;
        }

        setEvidence(null);
        setBotStatus(null);
        setScamLikelihood(0);
        setSearchResults([]);
        setTranscripts([]);
        setAnalysisResult(null);
        setThreatAssessment(null);
        setCallDuration(0);
        setDeepfakeDetected(false);
        setDeepfakeScore(0);
        setCallActions([]);
        setLiveUserTranscript('');
        setLiveAiTranscript('');

        let callSessionId = `demo_${Date.now()}`;
        try {
            callSessionId = await startDemoCall('Suspected Scammer', callSessionId);
            setCurrentCallSessionId(callSessionId);
            const optimisticIso = new Date().toISOString();
            setDemoCallState((prev) => ({
                ...(prev ?? { state: 'idle', updatedAt: null }),
                state: 'ringing',
                sessionId: callSessionId,
                callerName: prev?.callerName || 'Suspected Scammer',
                callerNumber: prev?.callerNumber || '+60 XX-XXXX XXXX',
                requiresAnswer: true,
                ownerDevice: null,
                ownerClientId: null,
                updatedAtIso: optimisticIso,
                updatedAt: prev?.updatedAt ?? null
            } as DemoCallDoc));
            // Start WebRTC audio bridge alongside the call
            startWebRTCCall().catch((err) => {
                console.warn('WebRTC audio bridge failed (call works without it):', err);
            });
            setUiNotice('Call is ringing. Victim must answer first.');
        } catch (e) {
            console.warn('Backend/Firebase call start unavailable (local-only mode):', e);
            setUiNotice('Unable to start demo call.');
        }
    };

    useEffect(() => {
        const callState = demoCallState?.state || 'idle';
        const sessionId = (demoCallState?.sessionId || currentCallSessionId || '').trim();
        if (callState === 'connected' && sessionId) {
            if (!callTimerRef.current) {
                callTimerRef.current = setInterval(() => {
                    setCallDuration(prev => prev + 1);
                }, 1000);
            }
            if (connectionState === ConnectionState.DISCONNECTED) {
                geminiService.connect(sessionId).catch((error) => {
                    console.error('Failed to start AI host session:', error);
                    setUiNotice('AI host failed to start.');
                });
            }
            return;
        }

        if (callTimerRef.current) {
            clearInterval(callTimerRef.current);
            callTimerRef.current = null;
        }
        setCallDuration(0);
        hadGeminiConnectionRef.current = false;

        if (connectionState === ConnectionState.CONNECTED) {
            geminiService.disconnect().catch(console.warn);
        }
        // Clean up WebRTC audio bridge
        cleanupWebRTC().catch(console.warn);
    }, [demoCallState?.state, demoCallState?.sessionId, currentCallSessionId, connectionState]);

    useEffect(() => {
        const callState = demoCallState?.state;
        const activeSessionId = (demoCallState?.sessionId || currentCallSessionId || '').trim();
        if (connectionState !== ConnectionState.DISCONNECTED) return;
        if (callState !== 'connected') return;
        if (!hadGeminiConnectionRef.current) return;
        if (!activeSessionId) return;

        endDemoCall(activeSessionId, ['ai_host_disconnected'], {
            endedBy: 'web_client',
            device: 'web',
            clientId: webClientIdRef.current
        }).catch(console.warn);
    }, [connectionState, demoCallState?.state, demoCallState?.sessionId, currentCallSessionId]);

    const handleVictimAnswer = async () => {
        const sessionId = (demoCallState?.sessionId || currentCallSessionId || '').trim();
        if (!sessionId) {
            setUiNotice('No active ringing session.');
            return;
        }
        try {
            const result = await answerDemoCall(sessionId, {
                device: 'web',
                clientId: webClientIdRef.current,
                answeredByLabel: 'Web Victim Panel'
            });
            if (!result.accepted) {
                setUiNotice('Call already answered on another device.');
            } else {
                const optimisticIso = new Date().toISOString();
                setDemoCallState((prev) => ({
                    ...(prev ?? { state: 'idle', updatedAt: null }),
                    state: 'connected',
                    sessionId,
                    ownerDevice: (result.owner_device ?? 'web') as 'web' | 'mobile' | null,
                    ownerClientId: result.owner_client_id ?? webClientIdRef.current,
                    answeredAtIso: optimisticIso,
                    answeredByLabel: prev?.answeredByLabel || 'Web Victim Panel',
                    updatedAtIso: optimisticIso,
                    updatedAt: prev?.updatedAt ?? null
                } as DemoCallDoc));
            }
        } catch (error) {
            setUiNotice((error as Error).message || 'Failed to answer call.');
        }
    };

    const handleVictimDecline = async () => {
        const sessionId = (demoCallState?.sessionId || currentCallSessionId || '').trim();
        if (!sessionId) return;
        try {
            await endDemoCall(sessionId, ['declined_by_web'], {
                endedBy: 'web_client',
                device: 'web',
                clientId: webClientIdRef.current
            });
        } catch (error) {
            setUiNotice((error as Error).message || 'Failed to decline call.');
        }
    };

    const handleVictimHangUp = async () => {
        const sessionId = (demoCallState?.sessionId || currentCallSessionId || '').trim();
        if (!sessionId) return;
        try {
            await endDemoCall(sessionId, ['hangup_by_web_owner'], {
                endedBy: 'web_client',
                device: 'web',
                clientId: webClientIdRef.current
            });
        } catch (error) {
            setUiNotice((error as Error).message || 'Only call owner can hang up.');
        }
    };
    const handleDirectorAction = (action: string) => {
        if (connectionState === ConnectionState.CONNECTED) {
            geminiService.sendLiveInstruction(action);
        }
    };

    const syncedCallState = (demoCallState?.state || 'idle') as 'idle' | 'ringing' | 'connected' | 'ended';
    const syncedSessionId = (demoCallState?.sessionId || currentCallSessionId || '').trim() || null;
    const ownerDevice = demoCallState?.ownerDevice || null;
    const ownerClientId = demoCallState?.ownerClientId || null;
    const isWebOwner = syncedCallState === 'connected' &&
        ownerDevice === 'web' &&
        ownerClientId === webClientIdRef.current;
    const victimReadOnly = syncedCallState === 'connected' && !isWebOwner;
    const inVictimCall = syncedCallState === 'ringing' || syncedCallState === 'connected';

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-800 via-slate-900 to-slate-800 text-gray-800 font-sans">

            {/* Header */}
            <header className="w-full p-4 flex items-center justify-between bg-slate-900/80 backdrop-blur-sm border-b border-slate-700 sticky top-0 z-10">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center text-xl">🛡️</div>
                    <div>
                        <h1 className="text-white font-bold">VeriCall Malaysia</h1>
                        <p className="text-slate-400 text-xs">Smart Call Screening Demo</p>
                    </div>
                </div>
                <div className="flex gap-2">
                    {evidence && (
                        <button onClick={() => setIsReportOpen(true)} className="bg-red-500/20 text-red-400 p-2 rounded-full text-xs font-bold animate-pulse">
                            <FileIcon />
                        </button>
                    )}
                    <button onClick={() => setIsTeachModalOpen(true)} className="bg-slate-700 text-slate-300 p-2 rounded-full text-xs font-bold hover:bg-slate-600">
                        <BookIcon />
                    </button>
                </div>
            </header>

            {/* Split Screen Layout */}
            <main className="flex items-start justify-center gap-8 p-8">
                {uiNotice && (
                    <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-slate-900 text-white px-4 py-2 rounded-lg text-sm border border-slate-700 shadow-xl">
                        {uiNotice}
                    </div>
                )}

                {/* LEFT SIDE: Scammer Phone (Uncle Ah Hock Interface) */}
                <div className="flex flex-col items-center gap-4">
                    <div className="text-center">
                        <h2 className="text-white font-bold text-lg">📞 Scammer Phone</h2>
                        <p className="text-slate-400 text-sm">You role-play as scammer</p>
                    </div>

                    <div className="w-full max-w-md bg-slate-50 rounded-3xl overflow-hidden border-4 border-slate-800 shadow-2xl flex flex-col" style={{ height: '700px' }}>
                        {/* Phone Header */}
                        <div className="p-4 flex items-center gap-3 bg-white border-b border-slate-200">
                            <div className="w-12 h-12 rounded-full overflow-hidden border-2 border-amber-500">
                                <img src="https://picsum.photos/200/200?random=1" alt="Uncle Ah Hock" className="w-full h-full object-cover" />
                            </div>
                            <div className="flex-1">
                                <h3 className="text-lg font-bold text-slate-900">Uncle Ah Hock</h3>
                                <p className="text-xs text-slate-500">
                                    {connectionState === ConnectionState.CONNECTED ? '🔴 In Call' : 'Ready to answer'}
                                </p>
                            </div>
                        </div>

                        {/* Phone Content */}
                        <div className="flex-1 flex flex-col p-4 gap-4 overflow-y-auto">
                            {/* Threat Level */}
                            <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
                                <div className="flex justify-between items-end mb-2">
                                    <span className="text-xs font-bold text-slate-400">THREAT LEVEL</span>
                                    <span className={`text-sm font-black px-2 py-0.5 rounded text-white ${scamLikelihood > 70 ? 'bg-red-600' : 'bg-green-500'}`}>
                                        {scamLikelihood}%
                                    </span>
                                </div>
                                <div className="w-full h-4 bg-slate-100 rounded-full overflow-hidden">
                                    <div className={`h-full transition-all duration-300 ${scamLikelihood > 70 ? 'bg-red-600' : 'bg-green-500'}`} style={{ width: `${scamLikelihood}%` }}></div>
                                </div>
                            </div>
                            <div className={`p-3 rounded-lg border text-xs font-semibold ${AUTO_HANGUP_ENABLED ? 'bg-red-50 border-red-200 text-red-700' : 'bg-amber-50 border-amber-200 text-amber-700'}`}>
                                Auto-hangup {AUTO_HANGUP_ENABLED ? 'armed' : 'shadow'} • Session {syncedSessionId ?? 'not_started'}
                            </div>
                            {callActions.length > 0 && (
                                <div className="bg-slate-900 text-slate-100 p-3 rounded-lg border border-slate-700">
                                    <div className="text-[11px] font-bold uppercase text-slate-300 mb-2">Call Action Timeline</div>
                                    <div className="space-y-1 max-h-20 overflow-y-auto">
                                        {callActions.map((item, idx) => (
                                            <div key={`${item.ts}_${idx}`} className="text-[11px]">
                                                [{new Date(item.ts).toLocaleTimeString()}] {item.action.toUpperCase()} {item.reasons[0] ? `- ${item.reasons[0]}` : ''}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Alerts */}
                            {botStatus && (
                                <div className="bg-red-900 text-white p-3 rounded-lg border border-red-500 animate-pulse flex items-center gap-2">
                                    <span className="text-2xl">🤖</span>
                                    <div>
                                        <div className="font-bold text-xs uppercase text-red-300">BOT DETECTED</div>
                                        <div className="text-sm font-bold">{botStatus.reason}</div>
                                    </div>
                                </div>
                            )}
                            {detectedPattern && (
                                <div className="bg-orange-600 text-white p-3 rounded-lg border border-orange-400 flex items-center gap-2">
                                    <span className="text-2xl">🚨</span>
                                    <div>
                                        <div className="font-bold text-xs uppercase text-orange-200">PATTERN MATCHED</div>
                                        <div className="text-sm font-bold">{detectedPattern}</div>
                                    </div>
                                </div>
                            )}

                            {/* Mode Switcher */}
                            <div className="flex bg-slate-200 p-1 rounded-lg">
                                <button onClick={() => setMode('call')} className={`flex-1 py-2 text-sm font-bold rounded-md ${mode === 'call' ? 'bg-white shadow' : 'text-slate-600'}`}>Voice</button>
                                <button onClick={() => setMode('text')} className={`flex-1 py-2 text-sm font-bold rounded-md ${mode === 'text' ? 'bg-white shadow' : 'text-slate-600'}`}>Text</button>
                            </div>

                            {/* Voice Mode */}
                            {mode === 'call' && (
                                <div className="flex flex-col items-center flex-1 space-y-4 bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
                                    <AudioVisualizer isSpeaking={connectionState === ConnectionState.CONNECTED && volume > 0.01} volume={volume} />

                                    <button onClick={handleConnect} disabled={connectionState === ConnectionState.CONNECTING} className={`w-20 h-20 rounded-full flex items-center justify-center shadow-xl transition-all ${connectionState === ConnectionState.CONNECTED ? 'bg-red-500 hover:bg-red-600' : 'bg-indigo-600 hover:bg-indigo-700'}`}>
                                        {connectionState === ConnectionState.CONNECTING ? <div className="w-8 h-8 border-4 border-white/30 border-t-white rounded-full animate-spin" /> : connectionState === ConnectionState.CONNECTED ? <PhoneOffIcon /> : <PhoneIcon />}
                                    </button>

                                    {connectionState === ConnectionState.CONNECTED && (
                                        <>
                                            <div className="w-full bg-slate-900 rounded-xl p-4 space-y-3 max-h-32 overflow-y-auto">
                                                <div className="text-xs font-bold text-slate-400 uppercase">📝 Live Transcript</div>
                                                {liveUserTranscript && (
                                                    <div className="flex items-start gap-2">
                                                        <span className="text-red-400 text-xs font-bold shrink-0">CALLER:</span>
                                                        <span className="text-red-200 text-sm">{liveUserTranscript}</span>
                                                    </div>
                                                )}
                                                {liveAiTranscript && (
                                                    <div className="flex items-start gap-2">
                                                        <span className="text-green-400 text-xs font-bold shrink-0">UNCLE:</span>
                                                        <span className="text-green-200 text-sm">{liveAiTranscript}</span>
                                                    </div>
                                                )}
                                            </div>
                                            <div className="grid grid-cols-2 gap-2 w-full">
                                                <button onClick={() => handleDirectorAction('Pretend you have a heart attack!')} className="bg-rose-100 text-rose-800 p-2 rounded-lg text-xs font-bold">💔 ATTACK</button>
                                                <button onClick={() => handleDirectorAction('Demand their ID number!')} className="bg-blue-100 text-blue-800 p-2 rounded-lg text-xs font-bold">👮 ASK ID</button>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                            {/* Text Mode */}
                            {mode === 'text' && (
                                <div className="flex flex-col flex-1">
                                    <div className="flex-1 overflow-y-auto bg-white rounded-xl shadow-inner border border-slate-200 p-4 mb-4 text-sm max-h-40" ref={scrollRef}>
                                        {transcripts.map((msg) => (
                                            <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} mb-2`}>
                                                <div className={`max-w-[85%] p-3 rounded-lg ${msg.sender === 'user' ? 'bg-indigo-100' : 'bg-white border border-gray-200'}`}>
                                                    {msg.text}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                    <form onSubmit={(e) => { e.preventDefault(); geminiService.processTextChat(textInput); setTextInput(''); }} className="relative">
                                        <input type="text" value={textInput} onChange={(e) => setTextInput(e.target.value)} placeholder="Type as scammer..." className="w-full p-3 pr-12 rounded-full border border-slate-300 shadow-sm text-sm" />
                                        <button type="submit" className="absolute right-2 top-1 p-2 bg-indigo-600 text-white rounded-full"><SendIcon /></button>
                                    </form>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* CENTER: Connection */}
                <div className="flex flex-col items-center justify-center gap-4 text-slate-500 pt-32">
                    <div className="text-4xl">📡</div>
                    <div className="w-px h-32 bg-gradient-to-b from-transparent via-slate-600 to-transparent"></div>
                    <div className={`text-xs font-medium px-3 py-1 rounded-full ${connectionState === ConnectionState.CONNECTED ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-300'}`}>
                        {connectionState === ConnectionState.CONNECTED ? 'Connected' : 'Waiting...'}
                    </div>
                    <div className="w-px h-32 bg-gradient-to-b from-transparent via-slate-600 to-transparent"></div>
                    <div className="text-4xl">🔍</div>
                </div>

                {/* RIGHT SIDE: Victim Phone */}
                <div className="flex flex-col items-center gap-4">
                    <div className="text-center">
                        <h2 className="text-white font-bold text-lg">📱 Victim Phone</h2>
                        <p className="text-slate-400 text-sm">Smart screening view</p>
                    </div>

                    <VictimPhone
                        isInCall={inVictimCall}
                        callState={syncedCallState}
                        callerName={demoCallState?.callerName || 'Unknown Caller'}
                        callerNumber={demoCallState?.callerNumber || '+60 XX-XXXX XXXX'}
                        ownerDevice={ownerDevice}
                        isOwner={isWebOwner}
                        isReadOnly={victimReadOnly}
                        scamLikelihood={scamLikelihood}
                        callerTranscript={liveUserTranscript}
                        uncleTranscript={liveAiTranscript}
                        analysisResult={analysisResult}
                        threatAssessment={threatAssessment}
                        callDuration={callDuration}
                        deepfakeDetected={deepfakeDetected}
                        deepfakeScore={deepfakeScore}
                        onAnswer={handleVictimAnswer}
                        onDecline={handleVictimDecline}
                        onEndCall={handleVictimHangUp}
                    />
                </div>

            </main>

            {/* REPORT MODAL */}
            {isReportOpen && evidence && (
                <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
                    <div className="bg-white w-full max-w-lg rounded-xl overflow-hidden shadow-2xl">
                        <div className="bg-blue-900 text-white p-4 flex justify-between items-center">
                            <h2 className="font-bold flex items-center gap-2"><FileIcon /> PDRM SCAM REPORT</h2>
                            <button onClick={() => setIsReportOpen(false)} className="text-blue-200 hover:text-white">✕</button>
                        </div>
                        <div className="p-6 font-mono text-xs overflow-y-auto max-h-[60vh] bg-slate-50">
                            <div className="border-b pb-4 mb-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>CASE ID: <span className="font-bold">{evidence.id}</span></div>
                                    <div>DATE: <span className="font-bold">{evidence.timestamp.toLocaleDateString()}</span></div>
                                    <div>DURATION: <span className="font-bold">{evidence.duration}s</span></div>
                                    <div>TYPE: <span className="font-bold text-red-600">{evidence.scamType}</span></div>
                                </div>
                            </div>
                            {evidence.classificationReason && (
                                <div className="mb-3 rounded border bg-white p-2 text-[10px]">
                                    <div><span className="font-bold">CLASSIFICATION REASON:</span> {evidence.classificationReason}</div>
                                    <div><span className="font-bold">MONEY REQUEST EVIDENCE:</span> {(evidence.moneyRequestEvidence && evidence.moneyRequestEvidence.length > 0) ? evidence.moneyRequestEvidence.join(', ') : 'No explicit money request detected'}</div>
                                </div>
                            )}
                            <pre className="whitespace-pre-wrap bg-white border p-2 rounded max-h-40 overflow-y-auto text-[10px]">
                                {evidence.fullTranscript}
                            </pre>
                        </div>
                        <div className="p-4 bg-slate-100 flex justify-end gap-2">
                            <button
                                onClick={async () => {
                                    if (evidence) {
                                        const collector = new EvidenceCollector();
                                        await pdrmSubmit.downloadPDFReport(evidence, collector);
                                    }
                                }}
                                className="bg-blue-600 text-white px-4 py-2 rounded font-bold text-sm hover:bg-blue-700"
                            >
                                📄 PDF Only
                            </button>
                            <button
                                onClick={async () => {
                                    console.log('🎵 Audio button clicked!');
                                    console.log('   Evidence:', evidence);
                                    console.log('   Has callRecording?', !!evidence?.callRecording);
                                    console.log('   callRecording size:', evidence?.callRecording?.size);

                                    if (evidence?.callRecording) {
                                        await pdrmSubmit.downloadAudioRecording(evidence);
                                    } else {
                                        alert('❌ No audio recording available!\n\nDebug info:\n' +
                                            `- Evidence exists: ${!!evidence}\n` +
                                            `- callRecording field: ${evidence?.callRecording}\n` +
                                            `- Check console for details`);
                                    }
                                }}
                                className={`px-4 py-2 rounded font-bold text-sm ${evidence?.callRecording
                                        ? 'bg-green-600 text-white hover:bg-green-700 cursor-pointer'
                                        : 'bg-gray-400 text-gray-200 cursor-not-allowed'
                                    }`}
                                disabled={!evidence?.callRecording}
                            >
                                🎵 Audio Only {!evidence?.callRecording && '(No Audio)'}
                            </button>
                            <button
                                onClick={async () => {
                                    if (evidence) {
                                        const collector = new EvidenceCollector();
                                        await pdrmSubmit.downloadCompletePackage(evidence, collector);
                                    }
                                }}
                                className="bg-red-600 text-white px-4 py-2 rounded font-bold text-sm hover:bg-red-700"
                            >
                                📦 Complete Package (ZIP)
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Teach Modal */}
            {isTeachModalOpen && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm p-4">
                        <h2 className="font-bold mb-4">Teach Uncle New Tricks</h2>
                        <textarea value={teachInput} onChange={(e) => setTeachInput(e.target.value)} className="w-full border p-2 rounded h-32 mb-4" placeholder="Describe new scam tactic..." />
                        <div className="flex justify-end gap-2">
                            <button onClick={() => setIsTeachModalOpen(false)} className="px-4 py-2 text-slate-500">Cancel</button>
                            <button onClick={() => { geminiService.teachTactic(teachInput); setIsTeachModalOpen(false); setTeachInput(''); }} className="px-4 py-2 bg-amber-500 text-white rounded">Teach</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default App;


