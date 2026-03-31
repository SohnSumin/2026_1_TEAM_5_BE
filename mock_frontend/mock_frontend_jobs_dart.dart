import 'dart:io';
import 'dart:convert';
import 'package:http/http.dart' as http;

/// 백엔드 API 주소 (로컬 서버 127.0.0.1 사용)
const String baseApiUrl = "http://127.0.0.1:8000/api";

class SeenearService {
  String? _accessToken;
  String? _role; // SENIOR or REQUESTER

  // --- [1] Auth & Profile Methods ---

  Future<void> requestOtp(String phoneNumber) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/auth/otp/request'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'phone_number': phoneNumber}),
    );
    if (response.statusCode == 200) {
      print("OTP 발송 성공: ${jsonDecode(response.body)['debug_otp']}");
    } else {
      throw Exception("OTP 요청 실패: ${response.body}");
    }
  }

  Future<Map<String, dynamic>> login(String phoneNumber, String otpCode) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'phone_number': phoneNumber, 'otp_code': otpCode}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      _accessToken = data['access_token'];
      _role = data['role'];
      return data;
    } else {
      throw Exception("로그인 실패: ${response.body}");
    }
  }

  Future<void> signupSenior({
    required String phoneNumber,
    required String name,
    required String gender,
    required int birthYear,
    required String authCode,
  }) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/auth/signup/senior'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'phone_number': phoneNumber,
        'name': name,
        'gender': gender,
        'birth_year': birthYear,
        'auth_code': authCode,
        'locations': [
          {
            'location_name': '기본 거점',
            'latitude': 37.5665,
            'longitude': 126.9780,
            'is_primary': true
          }
        ],
      }),
    );
    if (response.statusCode != 200)
      throw Exception("시니어 가입 실패: ${response.body}");
  }

  Future<void> signupRequester({
    required String phoneNumber,
    required String nickname,
    required String gender,
    required int birthYear,
  }) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/auth/signup/req'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'phone_number': phoneNumber,
        'nickname': nickname,
        'gender': gender,
        'birth_year': birthYear,
      }),
    );
    if (response.statusCode != 200)
      throw Exception("요청자 가입 실패: ${response.body}");
  }

  // --- [2] Location Methods (Senior Only) ---

  Future<List<dynamic>> getMyLocations() async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/locations/my'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body)['locations'];
    } else {
      throw Exception("거점 조회 실패: ${response.body}");
    }
  }

  Future<void> updateLocations(List<Map<String, dynamic>> locations) async {
    final response = await http.put(
      Uri.parse('$baseApiUrl/locations/my'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken'
      },
      body: jsonEncode({'locations': locations}),
    );
    if (response.statusCode != 200)
      throw Exception("거점 업데이트 실패: ${response.body}");
  }

  Future<void> deleteLocation(String locationId) async {
    final response = await http.delete(
      Uri.parse('$baseApiUrl/locations/my/$locationId'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode != 200)
      throw Exception("거점 삭제 실패: ${response.body}");
  }

  // --- [3] Job Methods ---

  // 공고 등록 (Requester)
  Future<Map<String, dynamic>> createJob({
    required String title,
    required String content,
    required String tag,
    required String date,
    required String time,
    required double lat,
    required double lon,
    required String locName,
  }) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/jobs'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken'
      },
      body: jsonEncode({
        'title': title,
        'content': content,
        'category_tag': tag,
        'job_date': date,
        'start_time': time,
        'latitude': lat,
        'longitude': lon,
        'location_name': locName,
        'reward': 10000,
        'image_urls': []
      }),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("공고 등록 실패: ${response.body}");
  }

  // 주변 공고 조회 (Senior)
  Future<List<dynamic>> getNearbyJobs(int range) async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/jobs/nearby?range=$range'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("주변 공고 조회 실패: ${response.body}");
  }

  // 공고 상세 조회
  Future<Map<String, dynamic>> getJobDetail(String postId) async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/jobs/$postId'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("공고 상세 조회 실패: ${response.body}");
  }

  // 내 공고 조회 (Requester)
  Future<List<dynamic>> getMyJobs() async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/jobs/my'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception("내 공고 조회 실패: ${response.body}");
    }
  }

  // 공고 수정 및 상태 변경 (Requester)
  Future<void> updateJob(String postId, Map<String, dynamic> updateData) async {
    final response = await http.patch(
      Uri.parse('$baseApiUrl/jobs/$postId'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken'
      },
      body: jsonEncode(updateData),
    );
    if (response.statusCode != 200)
      throw Exception("공고 수정 실패: ${response.body}");
  }

  // 공고 삭제 (Requester)
  Future<void> deleteJob(String postId) async {
    final response = await http.delete(
      Uri.parse('$baseApiUrl/jobs/$postId'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode != 200)
      throw Exception("공고 삭제 실패: ${response.body}");
  }

  String? get role => _role;

  // --- [4] Matching & Notification Methods ---

  /// 1. 시니어의 공고 지원 (Senior)
  Future<Map<String, dynamic>> applyJob(String postId) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/matches/apply'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken'
      },
      body: jsonEncode({'post_id': postId}),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("지원 실패: ${response.body}");
  }

  /// 2. 요청자의 직접 제안 (Requester)
  Future<Map<String, dynamic>> proposeJob(
      String postId, String seniorId) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/matches/propose'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken'
      },
      body: jsonEncode({
        'post_id': postId,
        'senior_id': seniorId,
      }),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("제안 실패: ${response.body}");
  }

  /// 3. 매칭 상태 변경 (수락/거절)
  Future<void> updateMatchStatus(String matchId, String status) async {
    final response = await http.patch(
      Uri.parse('$baseApiUrl/matches/$matchId/status'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken'
      },
      body: jsonEncode({'status': status}), // ACCEPTED or REJECTED
    );
    if (response.statusCode != 200)
      throw Exception("매칭 상태 변경 실패: ${response.body}");
  }

  /// 4. 내 알림 내역 조회
  Future<List<dynamic>> getNotifications() async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/matches/notifications'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("알림 조회 실패: ${response.body}");
  }

  /// 확정된 매칭 목록 조회
  Future<List<dynamic>> getActiveMatches() async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/matches/active'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("매칭 목록 조회 실패");
  }

  /// 소일거리 종료 완료
  Future<void> completeJob(String matchId) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/matches/$matchId/complete'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode != 200) throw Exception("업무 종료 처리 실패");
  }

  Future<List<dynamic>> getRecommendedJobs({int range = 4000}) async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/matches/recommend-jobs?range_m=$range'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("추천 공고 조회 실패: ${response.body}");
  }

  /// 내 공고의 태그와 일치하는 주변 시니어 추천 받기 (Requester용)
  Future<List<dynamic>> getRecommendedSeniors(String postId,
      {int range = 4000}) async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/matches/recommend-seniors/$postId?range_m=$range'),
      headers: {
        'Authorization': 'Bearer $_accessToken',
      },
    );

    if (response.statusCode == 200) {
      // 정상적으로 시니어 목록(List) 반환
      return jsonDecode(response.body);
    } else {
      throw Exception("시니어 추천 목록 조회 실패: ${response.body}");
    }
  }
}

String getInput(String prompt) {
  stdout.write('$prompt: ');
  return stdin.readLineSync(encoding: utf8) ?? "";
}

Future<void> handleNotificationFlow(SeenearService service) async {
  final notis = await service.getNotifications();
  print("\n--- 알림 내역 (${notis.length}건) ---");
  for (var n in notis) {
    print("- [${n['type']}] ${n['content']}");
    print("  (매칭ID: ${n['related_id']} / 읽음: ${n['is_read']})");
  }

  if (notis.isEmpty) return;

  final matchId = getInput("수락/거절할 매칭 ID (엔터 시 스킵)");
  if (matchId.isNotEmpty) {
    print("[1] 수락(ACCEPTED) [2] 거절(REJECTED)");
    final action = getInput("선택");
    final status = (action == '1') ? "ACCEPTED" : "REJECTED";
    await service.updateMatchStatus(matchId, status);
    print("처리가 완료되었습니다.");
  }
}

void main() async {
  final service = SeenearService();
  print("=== SEENEAR 통합 업무 테스트 클라이언트 ===");

  while (true) {
    try {
      print("\n[1] 로그인/OTP [2] 회원가입 [q] 종료");
      final choice = getInput("선택");
      if (choice == 'q') break;

      if (choice == '1') {
        final phone = getInput("전화번호");
        await service.requestOtp(phone);
        final otp = getInput("인증번호 (123456)");
        final loginRes = await service.login(phone, otp);

        if (!loginRes['is_registered']) {
          print("미가입 유저입니다. 2번 메뉴를 통해 가입하세요.");
          continue;
        }
        print("로그인 성공! 역할: ${service.role}");
        await runMainFlow(service);
      } else if (choice == '2') {
        print("유형: [1] 시니어 [2] 요청자");
        final type = getInput("선택");
        final phone = getInput("전화번호");
        if (type == '1') {
          await service.signupSenior(
              phoneNumber: phone,
              name: getInput("이름"),
              gender: "MALE",
              birthYear: 1955,
              authCode: "SEMO-2026");
        } else {
          await service.signupRequester(
              phoneNumber: phone,
              nickname: getInput("닉네임"),
              gender: "FEMALE",
              birthYear: 1980);
        }
        print("가입 완료! 이제 로그인을 진행하세요.");
      }
    } catch (e) {
      print("\n❌ 에러 발생: $e");
      print("다시 시도해 주세요.");
    }
  }
}

Future<void> runMainFlow(SeenearService service) async {
  while (true) {
    print("\n--- 메인 메뉴 (역할: ${service.role}) ---");
    print("[N] 알림함 확인 (신규 알림 체크)");
    print("[M] 확정된 매칭 관리 (업무 완료)");

    if (service.role == "SENIOR") {
      // 시니어는 이제 본인의 태그와 맞는 공고를 추천받습니다.
      print("[1] 내 맞춤형 공고 추천/지원 [2] 거점 관리 [q] 로그아웃");
    } else {
      print("[1] 공고 등록 [2] 내 공고 관리 [q] 로그아웃");
    }

    final mChoice = getInput("선택").toLowerCase();
    if (mChoice == 'q') break;

    if (mChoice == 'n') {
      await handleNotificationFlow(service);
      continue;
    }

    if (mChoice == 'm') {
      final matches = await service.getActiveMatches();
      if (matches.isEmpty) {
        print("확정된 매칭이 없습니다.");
        continue;
      }
      print("\n[현재 진행 중인 매칭]");
      for (var m in matches) {
        print("- 매칭ID: ${m['match_id']} (상태: ${m['status']})");
      }
      final target = getInput("종료할 매칭 ID (엔터 시 스킵)");
      if (target.isNotEmpty) {
        await service.completeJob(target);
        print("✅ 업무가 종료되었습니다!");
      }
      continue;
    }

    if (service.role == "SENIOR") {
      if (mChoice == '1') {
        final range = int.tryParse(getInput("검색 범위(m) (기본 4000)")) ?? 4000;
        // 수정된 추천 메서드 호출
        final jobs = await service.getRecommendedJobs(range: range);

        print("\n--- [내 맞춤 공고 목록] ---");
        print("(내 관심 태그와 일치하고 거점 주변인 공고만 표시됩니다)");
        for (var j in jobs) {
          print("- [${j['tag']}] ${j['title']} (ID: ${j['post_id']})");
          print("  위치: ${j['location_name']} / 보상: ${j['reward']}원");
        }

        final applyId = getInput("지원할 공고 ID (엔터 시 스킵)");
        if (applyId.isNotEmpty) {
          await service.applyJob(applyId);
          print("지원 완료!");
        }
      } else if (mChoice == '2') {
        await handleLocationMenu(service);
      }
    } else {
      // REQUESTER Flow
      if (mChoice == '1') {
        final title = getInput("제목");
        final content = getInput("내용");
        final tag = getInput("태그 (예: 산책, 청소, 운전)"); // 태그 입력 중요!

        final res = await service.createJob(
          title: title,
          content: content,
          tag: tag,
          date: "2026-04-01",
          time: "10:00:00",
          lat: 37.5665,
          lon: 126.9780,
          locName: "서울시청",
        );
        print("공고 등록 완료: ${res['post_id']}");
      } else if (mChoice == '2') {
        await handleJobManagement(service);
      }
    }
  }
}

Future<void> handleLocationMenu(SeenearService service) async {
  print("\n--- 거점 관리 ---");
  print("[1] 목록조회 [2] 일괄 업데이트(Mock) [3] 삭제");
  final lChoice = getInput("선택");
  if (lChoice == '1') {
    final locs = await service.getMyLocations();
    for (var l in locs)
      print(
          "- [${l['is_primary'] ? '기본' : '일반'}] ${l['location_name']} (${l['location_id']})");
  } else if (lChoice == '2') {
    await service.updateLocations([
      {
        'location_name': '서울역',
        'latitude': 37.5546,
        'longitude': 126.9706,
        'is_primary': true
      },
      {
        'location_name': '남산타워',
        'latitude': 37.5511,
        'longitude': 126.9881,
        'is_primary': false
      },
    ]);
    print("업데이트 완료");
  } else if (lChoice == '3') {
    await service.deleteLocation(getInput("삭제할 ID"));
    print("삭제 완료");
  }
}

Future<void> handleJobManagement(SeenearService service) async {
  final jobs = await service.getMyJobs();
  print("\n[내 공고 관리]");
  for (var j in jobs)
    print("- [${j['status']}] ${j['title']} (ID: ${j['post_id']})");

  final targetId = getInput("관리할 공고 ID (엔터 시 스킵)");
  if (targetId.isEmpty) return;

  // 5번 메뉴(시니어 추천)를 명시적으로 추가
  print("[1] 상세조회 [2] 수정 [3] 상태변경 [4] 삭제 [5] 맞춤 시니어 찾기 및 제안");
  final op = getInput("선택");

  if (op == '1') {
    print(await service.getJobDetail(targetId));
  } else if (op == '2') {
    await service.updateJob(targetId, {'title': getInput("새 제목")});
    print("수정 완료");
  } else if (op == '3') {
    final status = getInput("새 상태 (OPEN/MATCHED/DONE)");
    await service.updateJob(targetId, {'status': status});
    print("변경 완료");
  } else if (op == '4') {
    await service.deleteJob(targetId);
    print("삭제 완료");
  } else if (op == '5') {
    print("찾을 반경(m)을 입력하세요 (기본 4000):");
    final range = int.tryParse(getInput("반경")) ?? 4000;

    // 백엔드에서 태그 필터링이 먼저 수행됨
    final seniors = await service.getRecommendedSeniors(targetId, range: range);
    print("\n--- [내 공고 태그와 맞는 주변 시니어] ---");
    if (seniors.isEmpty) {
      print("조건에 맞는 시니어가 주변에 없습니다.");
    } else {
      for (var s in seniors) {
        print(
            "- [${s['name']}] (ID: ${s['user_id']}) / 신뢰도: ${s['trust_score']}");
        print("  태그: ${s['tags'] ?? '없음'}");
        print("  자기소개: ${s['bio_summary'] ?? '없음'}");
      }

      final seniorId = getInput("제안을 보낼 시니어 ID (엔터 시 취소)");
      if (seniorId.isNotEmpty) {
        await service.proposeJob(targetId, seniorId);
        print("✅ 시니어에게 해당 공고에 대한 업무 제안을 보냈습니다!");
      }
    }
  }
}
