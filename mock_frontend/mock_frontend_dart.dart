import 'dart:io';
import 'dart:convert';
import 'package:http/http.dart' as http;

/// 백엔드 API 주소 (로컬 CLI 실행 시 127.0.0.1 사용)
const String baseUrl = "http://127.0.0.1:8000/api/auth";

class AuthService {
  String? _accessToken;

  /// 1. 인증번호 발송 요청
  Future<void> requestOtp(String phoneNumber) async {
    final response = await http.post(
      Uri.parse('$baseUrl/otp/request'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'phone_number': phoneNumber}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      print("OTP 발송 성공: ${data['message']}");
      print("디버그용 OTP: ${data['debug_otp']}"); // 개발 단계 확인용
    } else {
      throw Exception("OTP 요청 실패: ${response.body}");
    }
  }

  /// 2. OTP 검증 및 로그인
  Future<Map<String, dynamic>> login(String phoneNumber, String otpCode) async {
    final response = await http.post(
      Uri.parse('$baseUrl/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'phone_number': phoneNumber, 'otp_code': otpCode}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      _accessToken = data['access_token'];
      print("로그인 결과: ${data['is_registered'] ? '기존 유저' : '신규 유저'}");
      return data;
    } else {
      throw Exception("로그인 실패: ${response.body}");
    }
  }

  /// 3. 시니어 회원가입
  Future<Map<String, dynamic>> signupSenior({
    required String phoneNumber,
    required String name,
    required String gender,
    required int birthYear,
    required String authCode,
    String? bioSummary,
    List<String>? tags,
  }) async {
    // 시니어는 최소 1개의 위치 정보가 필요함 (schemas.py: min_items=1)
    final response = await http.post(
      Uri.parse('$baseUrl/signup/senior'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'phone_number': phoneNumber,
        'name': name,
        'gender': gender,
        'birth_year': birthYear,
        'auth_code': authCode,
        'bio_summary': bioSummary,
        'tags': tags ?? [],
        'profile_icon': 'default_icon',
        'locations': [
          {
            'location_name': '기본 거점',
            'latitude': 37.5665,
            'longitude': 126.9780,
            'is_primary': true,
          }
        ],
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception("회원가입 실패: ${response.body}");
    }
  }

  /// 4. 요청자(보호자/기관) 회원가입
  Future<Map<String, dynamic>> signupRequester({
    required String phoneNumber,
    required String nickname,
    required String gender,
    required int birthYear,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/signup/req'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'phone_number': phoneNumber,
        'nickname': nickname,
        'gender': gender,
        'birth_year': birthYear,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception("요청자 회원가입 실패: ${response.body}");
    }
  }

  /// 5. 내 프로필 정보 조회
  Future<Map<String, dynamic>> getMyProfile() async {
    if (_accessToken == null) throw Exception("로그인이 필요합니다.");

    final response = await http.get(
      Uri.parse('$baseUrl/me'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken',
      },
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception("프로필 조회 실패: ${response.body}");
    }
  }

  /// 6. 회원 정보 수정
  Future<Map<String, dynamic>> updateProfile(
      Map<String, dynamic> updateData) async {
    if (_accessToken == null) throw Exception("로그인이 필요합니다. 먼저 로그인해주세요.");

    final response = await http.patch(
      Uri.parse('$baseUrl/me'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken',
      },
      body: jsonEncode(updateData),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception("정보 수정 실패: ${response.body}");
    }
  }

  /// 7. 회원 탈퇴 (OTP 인증 필요)
  Future<void> deleteAccount(String phoneNumber, String otpCode) async {
    if (_accessToken == null) throw Exception("로그인이 필요합니다.");

    final response = await http.delete(
      Uri.parse('$baseUrl/me'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken',
      },
      body: jsonEncode({'phone_number': phoneNumber, 'otp_code': otpCode}),
    );

    if (response.statusCode == 200) {
      _accessToken = null; // 탈퇴 성공 시 토큰 초기화
      print("회원 탈퇴 성공: ${jsonDecode(response.body)['message']}");
    } else {
      throw Exception("탈퇴 실패: ${response.body}");
    }
  }

  /// 9. 거점 목록 조회
  Future<List<dynamic>> getMyLocations() async {
    if (_accessToken == null) throw Exception("로그인이 필요합니다.");

    final response = await http.get(
      Uri.parse('${baseUrl.replaceAll('/auth', '/locations')}/my'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken',
      },
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body)['locations'];
    } else {
      throw Exception("거점 조회 실패: ${response.body}");
    }
  }

  /// 10. 거점 정보 수정
  Future<Map<String, dynamic>> updateMyLocation(
      List<Map<String, dynamic>> locations) async {
    if (_accessToken == null) throw Exception("로그인이 필요합니다.");

    final response = await http.put(
      Uri.parse('${baseUrl.replaceAll('/auth', '/locations')}/my'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken',
      },
      body: jsonEncode({'locations': locations}),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception("거점 수정 실패: ${response.body}");
    }
  }

  /// 11. 거점 삭제
  Future<void> deleteLocation(String locationId) async {
    if (_accessToken == null) throw Exception("로그인이 필요합니다.");

    final response = await http.delete(
      Uri.parse('${baseUrl.replaceAll('/auth', '/locations')}/my/$locationId'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken',
      },
    );

    if (response.statusCode == 200) {
      print("거점 삭제 성공: ${jsonDecode(response.body)['detail']}");
    } else {
      throw Exception("거점 삭제 실패: ${response.body}");
    }
  }
}

/// CLI 사용자 입력 보조 함수
String getInput(String prompt) {
  stdout.write('$prompt: ');
  return stdin.readLineSync(encoding: utf8) ?? "";
}

/// CLI 실행 메인 루프
void main() async {
  final authService = AuthService();
  print("=== SEENEAR CLI Mock Client ===");

  try {
    while (true) {
      print(
          "\n[1] 로그인/OTP요청  [2] 회원가입  [3] 정보수정  [4] 회원탈퇴  [5] 로그아웃  [6] 거점관리  [q] 종료");
      final choice = getInput("선택");

      if (choice == 'q') break;

      if (choice == '1') {
        final phone = getInput("전화번호 (-없이)");
        await authService.requestOtp(phone);

        final otp = getInput("인증번호 입력 (테스트: 123456)");
        final result = await authService.login(phone, otp);

        if (result['is_registered']) {
          print("로그인 성공! 토큰: ${result['access_token']}");
          final profile = await authService.getMyProfile();
          print("내 프로필 정보: $profile");
        } else {
          print("미가입 유저입니다. 회원가입을 먼저 진행해주세요.");
        }
      } else if (choice == '2') {
        print("\n가입 유형 선택: [1] 시니어  [2] 요청자");
        final type = getInput("유형");

        if (type == '1') {
          final code = getInput("복지관 인증코드 (예: SEMO-2026)");
          final phone = getInput("전화번호");
          final name = getInput("이름");
          final gender = getInput("성별 (MALE/FEMALE)");
          final birth = int.parse(getInput("출생년도 (예: 1950)"));
          final bio = getInput("한마디 각오 (예: 열심히 하겠습니다!)");
          final tagsInput = getInput("관심 태그 (예: 요리, 청소, 말벗 / 쉼표로 구분)");
          final tags = tagsInput
              .split(',')
              .map((e) => e.trim())
              .where((e) => e.isNotEmpty)
              .toList();

          final res = await authService.signupSenior(
            phoneNumber: phone,
            name: name,
            gender: gender,
            birthYear: birth,
            authCode: code,
            bioSummary: bio,
            tags: tags,
          );
          print("시니어 가입 성공: ${res['name']}님 (ID: ${res['user_id']})");
        } else if (type == '2') {
          final phone = getInput("전화번호");
          final gender = getInput("성별 (MALE/FEMALE)");
          final birth = int.parse(getInput("출생년도 (예: 1950)"));
          final nickname = getInput("닉네임");

          final res = await authService.signupRequester(
            phoneNumber: phone,
            nickname: nickname,
            gender: gender,
            birthYear: birth,
          );
          print("요청자 가입 성공! (ID: ${res['user_id']})");
        }
      } else if (choice == '3') {
        print("\n--- 정보 수정 시작 ---");
        // 먼저 현재 내 정보를 가져와서 역할을 확인
        final currentProfile = await authService.getMyProfile();
        Map<String, dynamic> updateData = {};

        if (currentProfile.containsKey('name')) {
          // 시니어인 경우
          print("[시니어 프로필 수정]");
          final newName = getInput("새 이름 (현재: ${currentProfile['name']})");
          final newBio =
              getInput("새 자기소개 (현재: ${currentProfile['bio_summary'] ?? '없음'})");

          if (newName.isNotEmpty) updateData['name'] = newName;
          if (newBio.isNotEmpty) updateData['bio_summary'] = newBio;
        } else if (currentProfile.containsKey('nickname')) {
          // 요청자인 경우
          print("[요청자 프로필 수정]");
          final newNick = getInput("새 닉네임 (현재: ${currentProfile['nickname']})");
          final newBirth = getInput("새 출생년도 (숫자만)");

          if (newNick.isNotEmpty) updateData['nickname'] = newNick;
          if (newBirth.isNotEmpty)
            updateData['birth_year'] = int.parse(newBirth);
        }

        if (updateData.isEmpty) {
          print("수정할 내용이 없어 취소합니다.");
          continue;
        }

        final res = await authService.updateProfile(updateData);
        print("수정 완료: $res");
      } else if (choice == '4') {
        print("\n--- 회원 탈퇴 (OTP 인증 필요) ---");
        final phone = getInput("본인 확인을 위한 전화번호");
        await authService.requestOtp(phone);

        final otp = getInput("인증번호 입력");
        await authService.deleteAccount(phone, otp);
      } else if (choice == '6') {
        print("\n--- 거점 관리 메뉴 ---");
        print("[1] 목록조회  [2] 거점 일괄 업데이트 (Mock Data)  [3] 거점 개별 삭제");
        final locChoice = getInput("선택");

        if (locChoice == '1') {
          final locations = await authService.getMyLocations();
          print("내 거점 목록 (${locations.length}개):");
          for (var loc in locations) {
            print(
                "- [${loc['is_primary'] ? '기본' : '일반'}] ${loc['location_name']} (ID: ${loc['location_id']})");
          }
        } else if (locChoice == '2') {
          print("\n[거점 일괄 업데이트 테스트]");
          print("기본 Mock 데이터를 넣으시겠습니까? (y/n)");
          final useMock = getInput("선택");

          List<Map<String, dynamic>> newLocations = [];

          if (useMock.toLowerCase() == 'y') {
            newLocations = [
              {
                'location_name': '서울역 (Mock)',
                'latitude': 37.5546,
                'longitude': 126.9706,
                'is_primary': true
              },
              {
                'location_name': '남산타워 (Mock)',
                'latitude': 37.5511,
                'longitude': 126.9881,
                'is_primary': false
              },
            ];
          } else {
            final count = int.tryParse(getInput("등록할 거점 개수 (1-3)")) ?? 1;
            for (int i = 0; i < count; i++) {
              print("\n[$i번째 거점 입력]");
              final name = getInput("거점 이름");
              final lat = double.parse(getInput("위도 (예: 37.5)"));
              final lon = double.parse(getInput("경도 (예: 127.0)"));
              final primary = getInput("기본 거점 여부 (y/n)") == 'y';

              newLocations.add({
                'location_name': name,
                'latitude': lat,
                'longitude': lon,
                'is_primary': primary,
              });
            }
          }

          final res = await authService.updateMyLocation(newLocations);
          print("거점 업데이트 완료! 현재 거점 개수: ${res['locations'].length}");
        } else if (locChoice == '3') {
          final locId = getInput("삭제할 거점 ID (UUID)");
          await authService.deleteLocation(locId);
        }
      } else {
        print("잘못된 선택입니다.");
      }
    }
  } catch (e) {
    print("\n[오류 발생] $e");
  }
}
