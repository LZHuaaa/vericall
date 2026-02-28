import React from 'react';
import { ThreatAssessment } from '../services/types/scamTypes';

interface VictimPhoneProps {
    isInCall: boolean;
    callState?: 'idle' | 'ringing' | 'connected' | 'ended';
    callerName?: string;
    callerNumber?: string;
    ownerDevice?: 'web' | 'mobile' | null;
    isOwner?: boolean;
    isReadOnly?: boolean;
    scamLikelihood: number;
    callerTranscript: string;
    uncleTranscript: string;
    analysisResult: {
        wavlmScore: number;
        isScam: boolean;
        scamType: string;
        confidence: number;
    } | null;
    threatAssessment?: ThreatAssessment | null;
    callDuration: number;
    deepfakeDetected?: boolean;
    deepfakeScore?: number;
    onAnswer?: () => void;
    onDecline?: () => void;
    onEndCall?: () => void;
}

const VictimPhone: React.FC<VictimPhoneProps> = ({
    isInCall,
    callState = 'idle',
    callerName = 'Unknown Caller',
    callerNumber = '+60 XX-XXXX XXXX',
    ownerDevice = null,
    isOwner = false,
    isReadOnly = false,
    scamLikelihood,
    callerTranscript,
    uncleTranscript,
    analysisResult,
    threatAssessment = null,
    callDuration,
    deepfakeDetected = false,
    deepfakeScore = 0,
    onAnswer,
    onDecline,
    onEndCall,
}) => {
    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
        const secs = (seconds % 60).toString().padStart(2, '0');
        return `${mins}:${secs}`;
    };

    const formatReasonCode = (code: string) => {
        if (code.startsWith('llm_urgency_')) {
            return `Urgency: ${code.replace('llm_urgency_', '').toUpperCase()}`;
        }
        if (code.startsWith('llm_red_flag_')) {
            return `Red flag: ${code.replace('llm_red_flag_', '').replace(/_/g, ' ')}`;
        }
        if (code.startsWith('llm_scam_type_')) {
            return `Scam intent: ${code.replace('llm_scam_type_', '').toUpperCase()}`;
        }
        if (code === 'retrieval_proxy_refused') {
            return 'Online verification blocked: invalid local proxy (127.0.0.1:9).';
        }
        if (code === 'retrieval_quota_exhausted') {
            return 'Online verification quota exceeded (Gemini 429).';
        }
        if (code === 'retrieval_connection_refused') {
            return 'Online verification connection was refused.';
        }
        if (code === 'degraded_mode_retrieval_failure') {
            return 'Running in local fallback mode due retrieval failure.';
        }
        return code.replace(/_/g, ' ');
    };

    const hasThreatAssessment = Boolean(threatAssessment);
    const riskLevel = threatAssessment?.risk_level;
    const isHighRisk = riskLevel === 'high' || riskLevel === 'critical';
    const hasSuspiciousReason = Boolean(
        threatAssessment?.reason_codes?.some(
            code => code.startsWith('llm_') || code.startsWith('deepfake_') || code.startsWith('retrieval_')
        )
    );
    const safeByStrictPolicy = Boolean(
        threatAssessment &&
        riskLevel === 'safe' &&
        threatAssessment.mode === 'normal' &&
        threatAssessment.retrieval_status === 'ok' &&
        !hasSuspiciousReason
    );
    const topReasonCodes = (threatAssessment?.reason_codes || [])
        .filter(code => code !== 'degraded_mode_retrieval_failure')
        .slice(0, 3);

    const normalizedCallState = callState || (isInCall ? 'connected' : 'idle');
    const screenState = normalizedCallState === 'ringing'
        ? 'screening'
        : normalizedCallState !== 'connected'
            ? 'idle'
            : !hasThreatAssessment
                ? 'screening'
                : isHighRisk
                    ? 'scam'
                    : safeByStrictPolicy
                        ? 'safe'
                        : 'caution';

    return (
        <div className="w-full max-w-md bg-slate-900 rounded-3xl overflow-hidden border-4 border-slate-800 shadow-2xl flex flex-col" style={{ height: '700px' }}>
            {screenState === 'idle' && (
                <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                    <div className="w-24 h-24 bg-slate-800 rounded-full flex items-center justify-center text-4xl mb-6">
                        Shield
                    </div>
                    <h3 className="text-white font-bold text-2xl mb-2">VeriCall Protected</h3>
                    <p className="text-slate-400">Your calls are being monitored for scams</p>
                    <p className="text-slate-500 text-sm mt-4">Waiting for incoming call...</p>
                </div>
            )}

            {screenState === 'screening' && (
                <div className="flex-1 flex flex-col">
                    <div className="bg-gradient-to-b from-indigo-600 to-indigo-800 p-6 text-center">
                        <div className="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4 relative">
                            <span className="text-3xl">Call</span>
                            <span className="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 rounded-full animate-pulse"></span>
                        </div>
                        <p className="text-indigo-200 text-sm">Incoming Call</p>
                        <h3 className="text-white font-bold text-xl">{callerName}</h3>
                        <p className="text-indigo-200 text-sm">{callerNumber}</p>
                    </div>

                    <div className="bg-amber-500/20 border-b border-amber-500/30 p-4 flex items-center gap-3">
                        <span className="text-xl">Scan</span>
                        <div className="flex-1">
                            <p className="text-amber-200 text-xs font-bold uppercase">Smart Screening Active</p>
                            <p className="text-white text-sm">Waiting for victim to answer...</p>
                        </div>
                        <div className="w-5 h-5 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
                    </div>

                    {deepfakeDetected && (
                        <div className="bg-gradient-to-r from-red-600 via-red-500 to-red-600 p-4 border-y-2 border-red-300">
                            <div className="text-center">
                                <p className="text-white font-black text-lg uppercase">AI Voice Signal</p>
                                <p className="text-red-100 text-sm font-bold">
                                    Deepfake score: {Math.round(deepfakeScore * 100)}%
                                </p>
                            </div>
                        </div>
                    )}

                    <div className="flex-1 p-4 space-y-4 overflow-y-auto">
                        <div className="bg-slate-800 rounded-xl p-3">
                            <p className="text-slate-400 text-xs font-bold mb-2">Call Transcript</p>
                            <div className="space-y-2 text-sm max-h-24 overflow-y-auto">
                                {uncleTranscript && (
                                    <div className="text-green-400">
                                        <span className="font-bold">Uncle:</span> {uncleTranscript}
                                    </div>
                                )}
                                {callerTranscript && (
                                    <div className="text-red-400">
                                        <span className="font-bold">Caller:</span> {callerTranscript}
                                    </div>
                                )}
                                {!uncleTranscript && !callerTranscript && (
                                    <div className="text-slate-500 italic">Waiting for speech...</div>
                                )}
                            </div>
                        </div>

                        <div className="bg-slate-800 rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-slate-400 text-xs font-bold uppercase">Threat Level</span>
                                <span className={`text-lg font-black ${scamLikelihood > 70 ? 'text-red-400' : scamLikelihood > 40 ? 'text-amber-400' : 'text-green-400'}`}>
                                    {scamLikelihood}%
                                </span>
                            </div>
                            <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                                <div
                                    className={`h-full transition-all duration-500 ${scamLikelihood > 70 ? 'bg-red-500' : scamLikelihood > 40 ? 'bg-amber-500' : 'bg-green-500'}`}
                                    style={{ width: `${scamLikelihood}%` }}
                                ></div>
                            </div>
                        </div>
                    </div>

                    <div className="p-4 bg-slate-800 grid grid-cols-2 gap-3">
                        <button
                            className="bg-slate-700 text-white py-3 rounded-xl font-medium hover:bg-slate-600 disabled:opacity-50"
                            onClick={onDecline}
                            disabled={normalizedCallState !== 'ringing'}
                        >
                            Decline
                        </button>
                        <button
                            className="bg-green-500 text-white py-3 rounded-xl font-medium hover:bg-green-600 disabled:opacity-50"
                            onClick={onAnswer}
                            disabled={normalizedCallState !== 'ringing' || isReadOnly}
                        >
                            Answer
                        </button>
                    </div>
                </div>
            )}

            {screenState === 'scam' && (
                <div className="flex-1 flex flex-col">
                    <div className="bg-gradient-to-b from-red-600 to-red-800 p-6 text-center">
                        <div className="text-5xl mb-3">Alert</div>
                        <h3 className="text-white font-black text-2xl mb-1">SCAM DETECTED</h3>
                        <p className="text-red-200 font-medium uppercase">{analysisResult?.scamType || 'Unknown'} Scam</p>
                    </div>

                    <div className="flex-1 p-4 space-y-4 overflow-y-auto">
                        <div className="grid grid-cols-2 gap-3">
                            <div className="bg-slate-800 rounded-xl p-3 text-center">
                                <p className="text-slate-400 text-xs">Deepfake Score</p>
                                <p className="text-red-400 font-black text-2xl">{Math.round((analysisResult?.wavlmScore || 0) * 100)}%</p>
                            </div>
                            <div className="bg-slate-800 rounded-xl p-3 text-center">
                                <p className="text-slate-400 text-xs">Confidence</p>
                                <p className="text-red-400 font-black text-2xl">{Math.round((analysisResult?.confidence || 0) * 100)}%</p>
                            </div>
                        </div>

                        <div className="bg-amber-500/20 border border-amber-400/30 rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    <span className="text-white font-bold">Uncle Handling Scammer</span>
                                </div>
                                <span className="text-amber-400 font-mono font-bold">{formatTime(callDuration)}</span>
                            </div>
                            <p className="text-amber-200 text-xs">Uncle Ah Hock is wasting scammer time.</p>
                        </div>
                        {isReadOnly && (
                            <div className="bg-slate-700 rounded-xl p-3 text-xs text-slate-100">
                                Active on {ownerDevice === 'mobile' ? 'mobile victim app' : 'web victim panel'}.
                                This screen is read-only mirror.
                            </div>
                        )}

                        <div className="bg-slate-800 rounded-xl p-3 text-xs text-slate-300">
                            <div className="font-bold text-slate-200 mb-1">Threat Engine</div>
                            <div>Version: {threatAssessment?.version || 'unknown'}</div>
                            <div>Mode: {threatAssessment?.mode || 'unknown'}</div>
                            <div>Retrieval: {threatAssessment?.retrieval_status || 'unknown'}</div>
                            <div>Call action: {(threatAssessment?.call_action || 'none').toUpperCase()}</div>
                        </div>
                    </div>

                    <div className="p-4 bg-slate-800 grid grid-cols-3 gap-2">
                        <button className="bg-slate-700 text-white py-3 rounded-xl text-xs font-medium hover:bg-slate-600">
                            Listen
                        </button>
                        <button
                            className="bg-red-500 text-white py-3 rounded-xl text-xs font-medium hover:bg-red-600 disabled:opacity-50"
                            onClick={onEndCall}
                            disabled={!isOwner}
                        >
                            End Call
                        </button>
                        <button className="bg-blue-500 text-white py-3 rounded-xl text-xs font-medium hover:bg-blue-600">
                            Report
                        </button>
                    </div>
                </div>
            )}

            {screenState === 'caution' && (
                <div className="flex-1 flex flex-col">
                    <div className="bg-gradient-to-b from-amber-500 to-amber-700 p-8 text-center">
                        <div className="text-5xl mb-3">Caution</div>
                        <h3 className="text-white font-black text-2xl mb-1">UNVERIFIED CALL</h3>
                        <p className="text-amber-100">No safe verification yet. Keep screening.</p>
                    </div>
                    <div className="flex-1 bg-slate-900 p-4 space-y-3 overflow-y-auto">
                        {isReadOnly && (
                            <div className="bg-slate-700 rounded-xl p-3 text-xs text-slate-100">
                                Active on {ownerDevice === 'mobile' ? 'mobile victim app' : 'web victim panel'}.
                                This screen is read-only mirror.
                            </div>
                        )}
                        <div className="bg-slate-800 rounded-xl p-3">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-slate-400 text-xs font-bold uppercase">Threat Level</span>
                                <span className="text-amber-300 font-black">{scamLikelihood}%</span>
                            </div>
                            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                                <div
                                    className={`h-full transition-all duration-500 ${scamLikelihood > 70 ? 'bg-red-500' : scamLikelihood > 40 ? 'bg-amber-500' : 'bg-green-500'}`}
                                    style={{ width: `${scamLikelihood}%` }}
                                ></div>
                            </div>
                        </div>
                        <div className="bg-slate-800 rounded-xl p-3 text-xs text-slate-300">
                            <div className="font-bold text-slate-200 mb-1">Threat Engine</div>
                            <div>Version: {threatAssessment?.version || 'unknown'}</div>
                            <div>Mode: {threatAssessment?.mode || 'unknown'}</div>
                            <div>Retrieval: {threatAssessment?.retrieval_status || 'unknown'}</div>
                            <div>Call action: {(threatAssessment?.call_action || 'none').toUpperCase()}</div>
                        </div>
                        {topReasonCodes.length > 0 && (
                            <div className="bg-slate-800 rounded-xl p-3">
                                <p className="text-slate-300 text-xs font-bold mb-2">Top Reasons</p>
                                <div className="space-y-1">
                                    {topReasonCodes.map(code => (
                                        <div key={code} className="text-xs text-amber-200">
                                            - {formatReasonCode(code)}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                    <div className="p-4 bg-slate-800 grid grid-cols-2 gap-3">
                        <button
                            className="bg-slate-700 text-white py-3 rounded-xl font-medium hover:bg-slate-600"
                            onClick={onDecline}
                        >
                            Decline
                        </button>
                        <button
                            className="bg-amber-500 text-white py-3 rounded-xl font-medium hover:bg-amber-600 disabled:opacity-50"
                            onClick={onEndCall}
                            disabled={!isOwner}
                        >
                            {isOwner ? 'End Call' : 'Read Only'}
                        </button>
                    </div>
                </div>
            )}

            {screenState === 'safe' && (
                <div className="flex-1 flex flex-col">
                    <div className="bg-gradient-to-b from-green-500 to-green-700 p-8 text-center">
                        <div className="text-5xl mb-3">OK</div>
                        <h3 className="text-white font-black text-2xl mb-1">LEGITIMATE CALL</h3>
                        <p className="text-green-100">No strong scam signals detected yet</p>
                    </div>
                    <div className="flex-1 bg-slate-900 p-6 flex flex-col items-center justify-center">
                        {isReadOnly && (
                            <div className="w-full bg-slate-700 rounded-xl p-3 text-xs text-slate-100 mb-4 text-center">
                                Active on {ownerDevice === 'mobile' ? 'mobile victim app' : 'web victim panel'}.
                                This screen is read-only mirror.
                            </div>
                        )}
                        <p className="text-slate-400 text-sm mb-3 text-center">
                            Uncle says: "Wait ah, I pass to owner..."
                        </p>
                        <p className="text-slate-500 text-xs mb-6 text-center">
                            Engine {threatAssessment?.version || 'unknown'} | Retrieval {threatAssessment?.retrieval_status || 'unknown'}
                        </p>
                        <button
                            className="w-full bg-green-500 text-white py-4 rounded-xl font-bold text-lg hover:bg-green-600 disabled:opacity-50"
                            onClick={onAnswer}
                            disabled={normalizedCallState !== 'ringing' || isReadOnly}
                        >
                            {normalizedCallState === 'ringing' ? 'Answer Call' : 'Connected'}
                        </button>
                    </div>
                    <div className="p-4 bg-slate-800 grid grid-cols-2 gap-3">
                        <button
                            className="bg-slate-700 text-white py-3 rounded-xl font-medium hover:bg-slate-600"
                            onClick={onDecline}
                        >
                            Decline
                        </button>
                        <button
                            className="bg-blue-500 text-white py-3 rounded-xl font-medium hover:bg-blue-600 disabled:opacity-50"
                            onClick={onEndCall}
                            disabled={!isOwner}
                        >
                            {isOwner ? 'End Call' : 'Read Only'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default VictimPhone;
