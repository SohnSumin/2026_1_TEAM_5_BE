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
      print("\n[1] 로그인/OTP요청  [2] 회원가입   [3] 탈퇴   [q] 종료");
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

          final res = await authService.signupSenior(
            phoneNumber: phone,
            name: name,
            gender: gender,
            birthYear: birth,
            authCode: code,
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
        print("탈퇴 기능은 아직 구현되지 않았습니다.");
      } else {
        print("잘못된 선택입니다.");
      }
    }
  } catch (e) {
    print("\n[오류 발생] $e");
  }
}
