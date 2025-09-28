using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace ForzaStudioCLI.Forza
{
    public static class Pvs
    {
        public static dynamic ReadPvs(string json)
        {
            return JsonConvert.DeserializeObject<dynamic>(json);
        }
    }
}
