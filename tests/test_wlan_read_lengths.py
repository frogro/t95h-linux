"""Extract real helper sources from the locked patch and exercise the correction."""
import hashlib,json,re,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ReadLengthTest(unittest.TestCase):
 def test_actual_helpers_and_patch_order(self):
  board=ROOT/'boards/t95h';base=board/'kernel'
  lock=json.loads((base/'source-lock.json').read_text());patch=(base/lock['patch']).read_text()
  functions=['__xradio_read_reg32','xradio_reg_read_32','xradio_apb_read_32','xradio_ahb_read_32']
  with tempfile.TemporaryDirectory() as tmp:
   tmp=Path(tmp);paths=[]
   for name in ['hwio.c','hwio.h']:
    rel='drivers/net/wireless/xradio/'+name
    entry=next(x for x in lock['files'] if x['path']==rel)
    section=patch.split('+++ b/'+rel+'\n',1)[1].split('\n--- ',1)[0]
    lines=section.splitlines(keepends=True)
    self.assertTrue(lines[0].startswith('@@ -0,0 '))
    content=''.join(x[1:] for x in lines if x.startswith('+'))+'\n'
    self.assertEqual(hashlib.sha256(content.encode()).hexdigest(),entry['sha256'])
    dest=tmp/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content);paths.append(dest)
   original='\n'.join(p.read_text() for p in paths)
   delta=base/'incremental/0001-xradio-fix-32bit-read-lengths.patch'
   subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(delta)],cwd=tmp,check=True,capture_output=True)
   for variant,text,expected in [('before',original,4),('after','\n'.join(p.read_text() for p in paths),0)]:
    helpers=[]
    for name in functions:
     m=re.search(r'static inline int '+name+r'\([^}]+\}',text);self.assertIsNotNone(m);helpers.append(m[0])
    code='''#include <stdint.h>
#include <stddef.h>
#include <string.h>
typedef uint16_t u16; typedef uint32_t u32;
struct xradio_common {int dummy;};
static size_t last;
static int rd(void*p,size_t n){last=n;memset(p,0x5a,n);return 0;}
static int __xradio_read(struct xradio_common*h,u16 a,void*p,size_t n,int z){return rd(p,n);}
static int xradio_reg_read(struct xradio_common*h,u16 a,void*p,size_t n){return rd(p,n);}
static int xradio_apb_read(struct xradio_common*h,u32 a,void*p,size_t n){return rd(p,n);}
static int xradio_ahb_read(struct xradio_common*h,u32 a,void*p,size_t n){return rd(p,n);}
'''+ '\n'.join(helpers)+'\nint main(void){_Static_assert(sizeof(void*)==8,"64bit");struct {u32 val,guard;} b;struct xradio_common h;int bad=0;\n'
    for name in functions:code+='b.val=0;b.guard=0x12345678;'+name+'(&h,0,&b.val);bad+=(last!=4||b.guard!=0x12345678);\n'
    code+='return bad;}';src=tmp/(variant+'.c');src.write_text(code);exe=tmp/variant
    subprocess.run(['cc','-O0',str(src),'-o',str(exe)],check=True)
    self.assertEqual(subprocess.run([str(exe)]).returncode,expected)
if __name__=='__main__':unittest.main()
