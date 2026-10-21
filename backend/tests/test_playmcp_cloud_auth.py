from __future__ import annotations

import copy
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

import httpx

from app.services.playmcp_cloud_auth import CloudPlayMcpTokenStore, GcsAuthObject
from app.services.saramin_recommendation import SaraminRecommendationUnavailable


class MemoryStorage:
    def __init__(self):
        self.data = {"access_token": "old", "refresh_token": "rotate-once", "client_id": "client", "expires_at": 0}
        self.generation = 1
        self.lock = threading.Lock()

    def read(self):
        with self.lock:
            return copy.deepcopy(self.data), str(self.generation)

    def write(self, data, generation):
        with self.lock:
            if str(self.generation) != generation:
                return None
            self.data = copy.deepcopy(data)
            self.generation += 1
            return str(self.generation)


class SharedAuthTest(unittest.TestCase):
    def setUp(self):
        self.storage = MemoryStorage()
        self.http = Mock()
        self.response = httpx.Response(200, json={"access_token": "new", "refresh_token": "next", "expires_in": 3600},
                                       request=httpx.Request("POST", "https://example.test"))
        self.http.post.return_value = self.response

    def test_refresh_survives_a_new_store_and_does_not_reuse_old_refresh(self):
        first = CloudPlayMcpTokenStore(self.storage, http_client=self.http)
        self.assertEqual(first.access_token(), "new")
        restarted = CloudPlayMcpTokenStore(self.storage, http_client=self.http)
        self.assertEqual(restarted.access_token(), "new")
        self.assertEqual(self.http.post.call_count, 1)
        self.assertEqual(self.storage.data["refresh_token"], "next")

    def test_two_instances_refresh_only_once(self):
        def post(*args, **kwargs):
            time.sleep(0.05)
            return self.response
        self.http.post.side_effect = post
        stores = [CloudPlayMcpTokenStore(self.storage, http_client=self.http) for _ in range(2)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(lambda store: store.access_token(), stores)), ["new", "new"])
        self.assertEqual(self.http.post.call_count, 1)

    def test_401_refresh_uses_other_instances_new_token(self):
        stores = [CloudPlayMcpTokenStore(self.storage, http_client=self.http) for _ in range(2)]
        self.storage.data["expires_at"] = time.time() + 3600
        for store in stores:
            self.assertEqual(store.access_token(), "old")
        self.assertEqual(stores[0].access_token(refresh=True), "new")
        self.assertEqual(stores[1].access_token(refresh=True), "new")
        self.assertEqual(self.http.post.call_count, 1)

    def test_uncertain_refresh_failure_keeps_lock_and_redacts_error(self):
        self.http.post.side_effect = RuntimeError("rotate-once must not leak")
        store = CloudPlayMcpTokenStore(self.storage, http_client=self.http)
        with self.assertRaises(SaraminRecommendationUnavailable) as caught:
            store.access_token()
        self.assertTrue(self.storage.data["refresh_in_progress"])
        self.assertNotIn("rotate-once", str(caught.exception))
        with patch("app.services.playmcp_cloud_auth.time.monotonic", side_effect=[0, 21]):
            with self.assertRaises(SaraminRecommendationUnavailable):
                store.access_token()
        self.assertEqual(self.http.post.call_count, 1)

    def test_storage_cas_412_is_contention_not_success(self):
        http = Mock()
        http.post.return_value = httpx.Response(412)
        storage = GcsAuthObject("private-bucket", http_client=http)
        with patch.object(storage, "_headers", return_value={"Authorization": "Bearer fake"}):
            self.assertIsNone(storage.write({"refresh_in_progress": True}, "7"))
        self.assertEqual(http.post.call_args.kwargs["params"]["ifGenerationMatch"], "7")

    def test_persistence_conflict_does_not_return_rotated_token(self):
        storage = Mock(wraps=self.storage)
        storage.write.side_effect = ["2", None]
        with self.assertRaises(SaraminRecommendationUnavailable):
            CloudPlayMcpTokenStore(storage, http_client=self.http).access_token()

    def test_late_401_does_not_rotate_new_token_in_same_store(self):
        self.storage.data["expires_at"] = time.time() + 3600
        store = CloudPlayMcpTokenStore(self.storage, http_client=self.http)
        rejected = store.access_token()
        self.assertEqual(store.refresh_after_rejection(rejected), "new")
        self.assertEqual(store.refresh_after_rejection(rejected), "new")
        self.assertEqual(self.http.post.call_count, 1)
