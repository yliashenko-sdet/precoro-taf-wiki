#!/usr/bin/env bash
# Грубий підрахунок показників боргу grep-ом. Аргумент: тека TAF-репозиторію.
cd "${1:-.}" || exit 1
c() { printf '%-40s %s\n' "$1" "$(grep -rE "$2" ${3:-src} --include='*.ts' | wc -l | tr -d ' ')"; }
c "allure.*"               'allure\.'                         src/ui
c "expect(await"           'expect\(await'                    src/ui/web/tests
c "waitForTimeout"         'waitForTimeout\('
c "catch(() => false)"     'catch\(\(\) => false\)'
c "catch(() => {})"        'catch\(\(\) => \{\}\)'
c "force: true"            'force: true'
c "clickUsingJavascript"   'clickUsingJavascript\('
c "doLogin/LoginPage in specs" 'doLogin\(|new LoginPage\('  src/ui/web/tests
c "db. in specs"           '\bdb\.[a-zA-Z]+\('               src/ui/web/tests
c "Constants."             'Constants\.'
c "mergeTests in specs"    'mergeTests\('                    src/ui/web/tests
c "xpath="                 'xpath='
c "this.xxxLocators."      'this\.[a-zA-Z]+Locators\.'       src/ui
printf '%-40s %s\n' "spec files > 1500 lines" "$(find src/ui/web/tests -name '*.spec.ts' -exec wc -l {} + | awk '$1>1500 && $2!="total"' | wc -l | tr -d ' ')"
