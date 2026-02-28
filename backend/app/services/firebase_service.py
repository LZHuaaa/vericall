"""
VeriCall Malaysia - Firebase Integration

Provides Firebase services for:
- User authentication
- Firestore database (scam patterns, family networks, user profiles)
- Cloud Messaging (push notifications for family alerts)

Setup:
1. Create Firebase project at https://console.firebase.google.com
2. Download service account key (Project Settings → Service accounts)
3. Save as backend/firebase-credentials.json
4. Set FIREBASE_CREDENTIALS_PATH in .env
"""
import os
import json
import secrets
from typing import Optional, Dict, List
from datetime import datetime, timedelta, timezone
import firebase_admin
from firebase_admin import credentials, firestore, messaging, auth
from app.config import config


class FirebaseService:
    """
    Firebase integration for VeriCall Malaysia.
    
    Provides:
    - Firestore: Store scam patterns, user profiles, family networks
    - FCM: Send alerts to family members
    - Auth: User authentication (optional)
    """
    
    def __init__(self):
        self._initialized = False
        self._db = None
    
    def initialize(self):
        """Initialize Firebase Admin SDK"""
        if self._initialized:
            return
        
        creds_path = config.FIREBASE_CREDENTIALS_PATH
        
        if not creds_path or not os.path.exists(creds_path):
            print("⚠️ Firebase credentials not found - running in demo mode")
            print(f"   Expected path: {creds_path}")
            print("   To enable Firebase:")
            print("   1. Create project at https://console.firebase.google.com")
            print("   2. Download service account key")
            print("   3. Set FIREBASE_CREDENTIALS_PATH in .env")
            return
        
        try:
            cred = credentials.Certificate(creds_path)
            firebase_admin.initialize_app(cred)
            self._db = firestore.client()
            self._initialized = True
            print("✅ Firebase initialized successfully")
        except Exception as e:
            print(f"❌ Firebase initialization error: {e}")
    
    @property
    def db(self):
        """Get Firestore client"""
        if not self._initialized:
            self.initialize()
        return self._db
    
    @property
    def is_available(self) -> bool:
        """Check if Firebase is available"""
        if not self._initialized:
            self.initialize()
        return self._initialized and self._db is not None
    
    # ═══════════════════════════════════════════════════════════
    # USER MANAGEMENT
    # ═══════════════════════════════════════════════════════════
    
    def create_user_profile(self, user_id: str, data: Dict) -> bool:
        """
        Create or update user profile in Firestore.
        
        Args:
            user_id: Firebase Auth UID or custom user ID
            data: User profile data
                - name: User's name
                - phone: Phone number
                - is_protected: If user is being protected (e.g., elderly parent)
                - family_members: List of family member IDs
                - fcm_token: Firebase Cloud Messaging token for notifications
        """
        if not self.is_available:
            print("⚠️ Firebase not available - skipping user creation")
            return False
        
        try:
            user_data = {
                **data,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            }
            
            self.db.collection("users").document(user_id).set(
                user_data, 
                merge=True
            )
            print(f"✅ User profile created/updated: {user_id}")
            return True
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return False
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile from Firestore"""
        if not self.is_available:
            return None
        
        try:
            doc = self.db.collection("users").document(user_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"❌ Error getting user: {e}")
            return None
    
    def update_fcm_token(self, user_id: str, fcm_token: str) -> bool:
        """Update user's FCM token for push notifications"""
        if not self.is_available:
            return False
        
        try:
            self.db.collection("users").document(user_id).update({
                "fcm_token": fcm_token,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            print(f"❌ Error updating FCM token: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════
    # FAMILY NETWORK
    # ═══════════════════════════════════════════════════════════
    
    def add_family_member(self, user_id: str, family_member_id: str) -> bool:
        """
        Add a family member to user's protection network.
        
        When user_id receives a scam call, family_member_id will be notified.
        """
        if not self.is_available:
            return False
        
        try:
            # Add to user's family list. Use set+merge so docs can be created lazily.
            self.db.collection("users").document(user_id).set({
                "family_members": firestore.ArrayUnion([family_member_id]),
                "updated_at": firestore.SERVER_TIMESTAMP
            }, merge=True)
            
            # Add reverse relationship (family_member protects user)
            self.db.collection("users").document(family_member_id).set({
                "protecting": firestore.ArrayUnion([user_id]),
                "updated_at": firestore.SERVER_TIMESTAMP
            }, merge=True)
            
            print(f"✅ Family link created: {family_member_id} protects {user_id}")
            return True
        except Exception as e:
            print(f"❌ Error adding family member: {e}")
            return False

    def generate_family_link_code(
        self,
        victim_id: str,
        victim_name: Optional[str] = None,
        ttl_minutes: int = 10
    ) -> Optional[Dict]:
        """
        Create one-time family link code with TTL.
        Returns dict: {code, expires_at, victim_id}
        """
        if not self.is_available:
            return None

        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        expires_at = int(datetime.now().timestamp() * 1000) + (ttl_minutes * 60 * 1000)

        try:
            code = None
            # Try a few times to avoid collisions.
            for _ in range(10):
                candidate = "".join(secrets.choice(alphabet) for _ in range(6))
                doc_ref = self.db.collection("family_links").document(candidate)
                if not doc_ref.get().exists:
                    code = candidate
                    break

            if not code:
                return None

            self.db.collection("family_links").document(code).set({
                "victim_id": victim_id,
                "victim_name": victim_name or "Protected User",
                "code": code,
                "expires_at": expires_at,
                "created_at": firestore.SERVER_TIMESTAMP
            })

            print(f"✅ Family link code generated for {victim_id}: {code}")
            return {
                "code": code,
                "expires_at": expires_at,
                "victim_id": victim_id
            }
        except Exception as e:
            print(f"❌ Error generating family link code: {e}")
            return None

    def consume_family_link_code(
        self,
        code: str,
        guardian_id: str,
        guardian_name: Optional[str] = None
    ) -> Dict:
        """
        Consume one-time family link code and create bi-directional relationship.
        """
        if not self.is_available:
            return {"success": False, "error": "Firebase not available"}

        try:
            normalized_code = code.strip().upper()
            doc_ref = self.db.collection("family_links").document(normalized_code)
            doc = doc_ref.get()

            if not doc.exists:
                return {"success": False, "error": "Invalid link code"}

            data = doc.to_dict() or {}
            expires_at = int(data.get("expires_at", 0))
            now_ms = int(datetime.now().timestamp() * 1000)
            if expires_at <= now_ms:
                # Expired codes are deleted on read.
                doc_ref.delete()
                return {"success": False, "error": "Link code expired"}

            victim_id = data.get("victim_id")
            if not victim_id:
                return {"success": False, "error": "Invalid link payload"}
            if victim_id == guardian_id:
                return {"success": False, "error": "Cannot link to self"}

            if not self.add_family_member(victim_id, guardian_id):
                return {"success": False, "error": "Failed to create family link"}

            # Save guardian profile metadata for easier display.
            if guardian_name:
                self.create_user_profile(guardian_id, {"name": guardian_name})

            # One-time code consumption.
            doc_ref.delete()
            print(f"✅ Family link code consumed: {normalized_code} ({guardian_id} -> {victim_id})")
            return {"success": True, "victim_id": victim_id}
        except Exception as e:
            print(f"❌ Error consuming family link code: {e}")
            return {"success": False, "error": str(e)}
    
    def get_family_members(self, user_id: str) -> List[Dict]:
        """Get all family members who should be notified for this user"""
        if not self.is_available:
            return []
        
        try:
            user = self.get_user_profile(user_id)
            if not user or "family_members" not in user:
                return []
            
            family = []
            for member_id in user["family_members"]:
                member = self.get_user_profile(member_id)
                if member:
                    family.append({
                        "id": member_id,
                        "name": member.get("name", "Unknown"),
                        "fcm_token": member.get("fcm_token")
                    })
            
            return family
        except Exception as e:
            print(f"❌ Error getting family: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════
    # SCAM REPORTS & INTELLIGENCE
    # ═══════════════════════════════════════════════════════════
    
    def report_scam(self, report_data: Dict) -> Optional[str]:
        """
        Save a scam report to community database.
        
        Args:
            report_data:
                - user_id: Reporter's ID
                - scam_type: lhdn, police, bank, family
                - phone_number: Scammer's phone number
                - transcript: Call transcript (optional)
                - deepfake_score: Detection score
                - location: User's location (optional)
        """
        if not self.is_available:
            return None
        
        try:
            report = {
                **report_data,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "verified": False,
                "report_count": 1
            }
            
            doc_ref = self.db.collection("scam_reports").add(report)
            print(f"✅ Scam report saved: {doc_ref[1].id}")
            return doc_ref[1].id
        except Exception as e:
            print(f"❌ Error saving report: {e}")
            return None
    
    def get_recent_scams(self, scam_type: str = None, limit: int = 20) -> List[Dict]:
        """Get recent scam reports from community database"""
        if not self.is_available:
            return []
        
        try:
            query = self.db.collection("scam_reports")\
                .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                .limit(limit)
            
            if scam_type:
                query = query.where("scam_type", "==", scam_type)
            
            reports = []
            for doc in query.stream():
                report = doc.to_dict()
                report["id"] = doc.id
                reports.append(report)
            
            return reports
        except Exception as e:
            print(f"❌ Error getting scams: {e}")
            return []
    
    def get_scam_stats(self) -> Dict:
        """Get aggregated scam statistics"""
        if not self.is_available:
            return {"error": "Firebase not available"}
        
        try:
            # Get count by type
            stats = {
                "total": 0,
                "by_type": {},
                "last_24h": 0
            }
            
            reports = self.db.collection("scam_reports").stream()
            for doc in reports:
                stats["total"] += 1
                data = doc.to_dict()
                scam_type = data.get("scam_type", "unknown")
                stats["by_type"][scam_type] = stats["by_type"].get(scam_type, 0) + 1
            
            return stats
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {"error": str(e)}
    
    # ═══════════════════════════════════════════════════════════
    # EVIDENCE STORAGE
    # ═══════════════════════════════════════════════════════════
    
    def save_evidence(self, report_id: str, evidence_data: Dict) -> bool:
        """
        Save detailed evidence linked to a scam report.
        
        Args:
            report_id: ID of the scam report
            evidence_data:
                - transcript: Full conversation transcript
                - audio_url: URL to stored audio (optional)
                - evidence_hash: SHA-256 hash for integrity
                - quality_score: 0-100 evidence completeness
                - keywords_detected: List of scam keywords found
                - verification_qa: List of verification Q&A attempts
        """
        if not self.is_available:
            print("⚠️ Firebase not available - skipping evidence save")
            return False
        
        try:
            evidence = {
                "report_id": report_id,
                **evidence_data,
                "timestamp": firestore.SERVER_TIMESTAMP
            }
            
            doc_ref = self.db.collection("evidence").add(evidence)
            print(f"✅ Evidence saved: {doc_ref[1].id}")
            return True
        except Exception as e:
            print(f"❌ Error saving evidence: {e}")
            return False
    
    def get_evidence_by_report(self, report_id: str) -> List[Dict]:
        """Get all evidence for a scam report"""
        if not self.is_available:
            return []
        
        try:
            docs = self.db.collection("evidence")\
                .where("report_id", "==", report_id)\
                .stream()
            
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            print(f"❌ Error getting evidence: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════
    # ANALYTICS & PATTERN TRACKING
    # ═══════════════════════════════════════════════════════════
    
    def track_scam_pattern(self, pattern_type: str, keywords: List[str]) -> bool:
        """
        Track scam pattern for analytics.
        
        Increments count and updates keywords for the pattern type.
        Used to identify trending scam tactics.
        
        Args:
            pattern_type: Type of scam (macau_scam, bank_scam, etc.)
            keywords: Keywords detected in this instance
        """
        if not self.is_available:
            return False
        
        try:
            pattern_ref = self.db.collection("scam_patterns").document(pattern_type)
            pattern_ref.set({
                "pattern_type": pattern_type,
                "keywords": firestore.ArrayUnion(keywords),
                "report_count": firestore.Increment(1),
                "last_seen": firestore.SERVER_TIMESTAMP
            }, merge=True)
            
            print(f"📊 Pattern tracked: {pattern_type}")
            return True
        except Exception as e:
            print(f"❌ Error tracking pattern: {e}")
            return False
    
    def get_trending_patterns(self, limit: int = 10) -> List[Dict]:
        """Get most common scam patterns"""
        if not self.is_available:
            return []
        
        try:
            docs = self.db.collection("scam_patterns")\
                .order_by("report_count", direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()
            
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            print(f"❌ Error getting patterns: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════
    # PUSH NOTIFICATIONS (FCM)
    # ═══════════════════════════════════════════════════════════
    
    def send_family_alert(
        self, 
        protected_user_id: str, 
        scam_type: str, 
        risk_level: str
    ) -> Dict:
        """
        Send push notification to all family members when scam detected.
        
        Args:
            protected_user_id: User who received the scam call
            scam_type: Type of scam detected
            risk_level: low, medium, high, critical
            
        Returns:
            Dict with success count and failures
        """
        if not self.is_available:
            return {"error": "Firebase not available", "sent": 0}
        
        # Get protected user's info
        protected_user = self.get_user_profile(protected_user_id)
        if not protected_user:
            return {"error": "User not found", "sent": 0}
        
        user_name = protected_user.get("name", "Family member")
        
        # Get family members with FCM tokens
        family = self.get_family_members(protected_user_id)
        
        results = {"sent": 0, "failed": 0, "no_token": 0}
        
        for member in family:
            fcm_token = member.get("fcm_token")
            
            if not fcm_token:
                results["no_token"] += 1
                continue
            
            try:
                # Create notification
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=f"🚨 Scam Alert: {user_name}",
                        body=f"{scam_type.upper()} scam detected! Risk: {risk_level}"
                    ),
                    data={
                        "type": "scam_alert",
                        "protected_user_id": protected_user_id,
                        "protected_user_name": user_name,
                        "scam_type": scam_type,
                        "risk_level": risk_level,
                        "timestamp": datetime.now().isoformat()
                    },
                    token=fcm_token
                )
                
                # Send notification
                response = messaging.send(message)
                print(f"✅ Alert sent to {member['name']}: {response}")
                results["sent"] += 1
                
            except Exception as e:
                print(f"❌ Failed to send to {member['name']}: {e}")
                results["failed"] += 1
        
        # Log the alert
        self.db.collection("alerts").add({
            "protected_user_id": protected_user_id,
            "scam_type": scam_type,
            "risk_level": risk_level,
            "family_notified": results["sent"],
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        
        return results
    
    def send_test_notification(self, fcm_token: str) -> bool:
        """Send a test notification to verify FCM setup"""
        if not self.is_available:
            return False
        
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title="🛡️ VeriCall Test",
                    body="Push notifications are working!"
                ),
                token=fcm_token
            )
            
            response = messaging.send(message)
            print(f"✅ Test notification sent: {response}")
            return True
        except Exception as e:
            print(f"❌ Test notification failed: {e}")
            return False
    def upsert_demo_call_state(self, data: Dict) -> bool:
        """Update the single demo call document consumed by web/mobile clients."""
        if not self.is_available:
            return False
        try:
            payload = {
                **data,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
            events = payload.pop("events", None)
            if isinstance(events, list) and events:
                payload["events"] = firestore.ArrayUnion(events)
            self.db.collection("calls").document("current_demo").set(payload, merge=True)
            return True
        except Exception as e:
            print(f"Error upserting demo call state: {e}")
            return False

    def get_demo_call_state(self) -> Optional[Dict]:
        """Get the single demo call document."""
        if not self.is_available:
            return None
        try:
            doc = self.db.collection("calls").document("current_demo").get()
            if not doc.exists:
                return None
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data
        except Exception as e:
            print(f"Error getting demo call state: {e}")
            return None

    def get_demo_victim_profile(self, victim_user_id: str) -> Optional[Dict]:
        """Load demo victim user profile for call push routing."""
        if not self.is_available:
            return None
        try:
            doc = self.db.collection("users").document(victim_user_id).get()
            if not doc.exists:
                return None
            return {"id": doc.id, **(doc.to_dict() or {})}
        except Exception as e:
            print(f"Error loading demo victim profile {victim_user_id}: {e}")
            return None

    def send_demo_incoming_call_push(
        self,
        victim_user_id: str,
        session_id: str,
        caller_name: str,
        caller_number: str,
    ) -> bool:
        """Send high-priority incoming call push for the victim demo app."""
        if not self.is_available:
            return False
        try:
            victim = self.get_demo_victim_profile(victim_user_id) or {}
            token = victim.get("fcm_token")
            if not token:
                print(f"No FCM token found for demo victim {victim_user_id}")
                return False

            message = messaging.Message(
                notification=messaging.Notification(
                    title="Incoming call detected",
                    body=f"{caller_name} ({caller_number})",
                ),
                data={
                    "type": "incoming_demo_call",
                    "session_id": session_id,
                    "caller_name": caller_name,
                    "caller_number": caller_number,
                    "victim_user_id": victim_user_id,
                    "ts": datetime.now().isoformat(),
                },
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        priority="high",
                        default_vibrate_timings=True,
                    ),
                ),
                token=token,
            )
            messaging.send(message)
            return True
        except Exception as e:
            print(f"Failed to send incoming-call push: {e}")
            return False
    def get_alerts_for_user(self, user_id: str, limit: int = 20) -> List[Dict]:
        """
        Get alerts relevant to a user.

        Returns alerts for:
        - the user as protected user
        - users they are protecting (guardian view)
        """
        if not self.is_available:
            return []

        try:
            profile = self.get_user_profile(user_id) or {}
            protecting_ids = profile.get("protecting", []) or []
            target_ids = list(dict.fromkeys([user_id, *protecting_ids]))

            def _fetch_alert_docs_for_user(protected_id: str, fetch_limit: int):
                base_query = self.db.collection("alerts").where(
                    "protected_user_id", "==", protected_id
                )
                try:
                    return list(
                        base_query
                        .order_by("timestamp", direction=firestore.Query.DESCENDING)
                        .limit(fetch_limit)
                        .stream()
                    )
                except Exception as exc:
                    # Demo fallback when composite indexes are not deployed yet.
                    if "requires an index" in str(exc).lower():
                        return list(base_query.limit(fetch_limit).stream())
                    raise

            docs = []
            each_limit = limit if len(target_ids) <= 1 else max(1, (limit // len(target_ids)) + 1)
            each_limit = max(5, each_limit)

            for protected_id in target_ids:
                docs.extend(_fetch_alert_docs_for_user(protected_id, each_limit))

            protected_cache: Dict[str, str] = {}
            alerts = []
            for doc in docs:
                data = doc.to_dict()
                protected_id = data.get("protected_user_id")
                if protected_id:
                    if protected_id not in protected_cache:
                        p = self.get_user_profile(protected_id) or {}
                        protected_cache[protected_id] = p.get(
                            "name", "Protected User"
                        )
                    data["protected_user_name"] = protected_cache[protected_id]

                ts = data.get("timestamp")
                if hasattr(ts, "isoformat"):
                    data["timestamp"] = ts.isoformat()
                elif hasattr(ts, "to_datetime"):
                    data["timestamp"] = ts.to_datetime().isoformat()
                elif ts is None:
                    data["timestamp"] = datetime.now().isoformat()
                else:
                    data["timestamp"] = str(ts)

                data["id"] = doc.id
                alerts.append(data)

            alerts.sort(key=lambda a: a.get("timestamp", ""), reverse=True)
            return alerts[:limit]
        except Exception as e:
            print(f"❌ Error getting alerts for user {user_id}: {e}")
            raise RuntimeError(f"alerts_query_failed: {e}") from e

    def save_threat_session(self, session_id: str, data: Dict) -> bool:
        """Create or update threat session metadata."""
        if not self.is_available:
            return False
        try:
            payload = {
                **data,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
            if "created_at" not in payload:
                payload["created_at"] = firestore.SERVER_TIMESTAMP
            self.db.collection("threat_sessions").document(session_id).set(
                payload,
                merge=True,
            )
            return True
        except Exception as e:
            print(f"Error saving threat session {session_id}: {e}")
            return False

    def get_threat_session(self, session_id: str) -> Optional[Dict]:
        """Get threat session document."""
        if not self.is_available:
            return None
        try:
            doc = self.db.collection("threat_sessions").document(session_id).get()
            if not doc.exists:
                return None
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data
        except Exception as e:
            print(f"Error loading threat session {session_id}: {e}")
            return None

    def save_threat_assessment(self, session_id: str, assessment: Dict) -> bool:
        """Append one threat assessment event to timeline."""
        if not self.is_available:
            return False
        try:
            payload = {
                **assessment,
                "session_id": session_id,
                "created_at": firestore.SERVER_TIMESTAMP,
            }
            self.db.collection("threat_assessments").add(payload)
            return True
        except Exception as e:
            print(f"Error saving threat assessment {session_id}: {e}")
            return False

    def get_threat_assessments(self, session_id: str, limit: int = 100) -> List[Dict]:
        """Get threat assessment timeline."""
        if not self.is_available:
            return []
        try:
            docs = (
                self.db.collection("threat_assessments")
                .where("session_id", "==", session_id)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )
            rows = []
            for doc in docs:
                item = doc.to_dict() or {}
                item["id"] = doc.id
                created_at = item.get("created_at")
                if hasattr(created_at, "isoformat"):
                    item["created_at"] = created_at.isoformat()
                rows.append(item)
            rows.sort(key=lambda x: x.get("created_at", ""))
            return rows
        except Exception as e:
            print(f"Error loading threat assessments {session_id}: {e}")
            return []

    def upsert_threat_pattern(self, pattern_id: str, data: Dict, ttl_days: int = 30) -> bool:
        """Store normalized threat pattern with TTL metadata."""
        if not self.is_available:
            return False
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
            payload = {
                **data,
                "pattern_id": pattern_id,
                "report_count": firestore.Increment(1),
                "expires_at": expires_at,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
            self.db.collection("threat_patterns").document(pattern_id).set(
                payload,
                merge=True,
            )
            return True
        except Exception as e:
            print(f"Error upserting threat pattern {pattern_id}: {e}")
            return False

# Singleton instance
firebase_service = FirebaseService()



