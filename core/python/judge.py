from __future__ import annotations

import ast
import re
from pathlib import Path

from core.python.runner import PythonRunner
from core.python.workspace import split_template, validate_template
from models.python.grading import JudgeDetail, PythonJudgeResult
from models.python.question import CodeFeaturePoint, CodeFeatureRule, ExecutionPoint, OutputPoint, PythonQuestion


class PythonJudge:
    def __init__(self, runner: PythonRunner | None = None):
        self.runner = runner or PythonRunner()

    def judge(self, question: PythonQuestion, source: str, file_path: Path) -> PythonJudgeResult:
        valid, message = validate_template(question.code, source)
        if not valid:
            return PythonJudgeResult(0, question.full_score, message=message)
        try:
            ast.parse(source)
            _before, program, _after = split_template(source)
            program_tree = ast.parse(program)
        except (SyntaxError, ValueError) as exc:
            return PythonJudgeResult(0, question.full_score, message=f"语法检查失败：{exc}")

        execution = next((p for p in question.grading_points if isinstance(p, ExecutionPoint)), None)
        outputs = [p for p in question.grading_points if isinstance(p, OutputPoint)]
        cases = [(point, case) for point in outputs for case in point.cases]
        if not cases:
            cases = [(None, None)]
        run_results = []
        timeout = execution.timeout_seconds if execution else 3.0
        for _point, case in cases:
            run_results.append(self.runner.run(file_path, case.stdin if case else "", timeout))
        if any(not result.success for result in run_results):
            failed = next(result for result in run_results if not result.success)
            reason = "运行超时" if failed.timed_out else (failed.stderr.strip() or "程序运行失败")
            detail = JudgeDetail(execution.id if execution else "execution", execution.name if execution else "程序运行", 0, execution.score if execution else 0, False, reason)
            return PythonJudgeResult(0, question.full_score, [detail], False, reason)

        details: list[JudgeDetail] = []
        earned = 0.0
        if execution:
            earned += execution.score
            details.append(JudgeDetail(execution.id, execution.name, execution.score, execution.score, True, "全部测试均正常退出"))

        result_index = 0
        for point in outputs:
            passed = 0
            messages = []
            for case in point.cases:
                actual = run_results[result_index].stdout
                result_index += 1
                ok = self._compare(actual, case.expected_stdout, point.compare_mode)
                passed += int(ok)
                messages.append(f"{case.id}: {'通过' if ok else '输出不匹配'}")
            ratio = passed / len(point.cases) if point.cases else 0.0
            point_earned = point.score * ratio
            earned += point_earned
            details.append(JudgeDetail(point.id, point.name, point_earned, point.score, passed == len(point.cases), "；".join(messages)))

        for point in (p for p in question.grading_points if isinstance(p, CodeFeaturePoint)):
            matched_weight = sum(rule.weight for rule in point.rules if self._matches(program_tree, rule))
            total_weight = sum(rule.weight for rule in point.rules)
            ratio = matched_weight / total_weight if total_weight else 0.0
            score_ratio = min(ratio / point.minimum_match_ratio, 1.0) if point.minimum_match_ratio > 0 else 1.0
            point_earned = point.score * score_ratio
            earned += point_earned
            details.append(JudgeDetail(point.id, point.name, point_earned, point.score, ratio >= point.minimum_match_ratio, f"命中比例 {ratio:.0%}，满分标准 {point.minimum_match_ratio:.0%}"))

        return PythonJudgeResult(round(min(earned, question.full_score), 2), question.full_score, details, True, "判分完成")

    @staticmethod
    def _normalize(value: str) -> str:
        return "\n".join(line.rstrip() for line in value.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n"))

    def _compare(self, actual: str, expected: str, mode: str) -> bool:
        actual_n, expected_n = self._normalize(actual), self._normalize(expected)
        if mode == "contains":
            return expected_n in actual_n
        if mode == "regex":
            return re.search(expected, actual_n, re.MULTILINE) is not None
        if mode == "lines_unordered":
            return sorted(actual_n.splitlines()) == sorted(expected_n.splitlines())
        return actual_n == expected_n

    @staticmethod
    def _matches(tree: ast.AST, rule: CodeFeatureRule) -> bool:
        nodes = list(ast.walk(tree))
        if rule.kind == "function_definition":
            return any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == rule.value for node in nodes)
        if rule.kind == "function_call":
            return any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == rule.value for node in nodes)
        if rule.kind == "method_call":
            return any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == rule.value for node in nodes)
        if rule.kind == "return_name":
            return any(isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == rule.value for node in nodes)
        if rule.kind == "name":
            return any(isinstance(node, ast.Name) and node.id == rule.value for node in nodes)
        syntax_types = {
            "slice": ast.Slice, "for": ast.For, "while": ast.While, "if": ast.If,
            "list_comprehension": ast.ListComp, "try": ast.Try,
        }
        return rule.kind == "syntax" and rule.value in syntax_types and any(isinstance(node, syntax_types[rule.value]) for node in nodes)
