#include "llvm/IR/Function.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/raw_ostream.h"

using namespace llvm;

namespace {

struct DemoPrintPass : public PassInfoMixin<DemoPrintPass> {
  PreservedAnalyses run(Function &F, FunctionAnalysisManager &) {
    errs() << "DemoPass: " << F.getName() << "\n";
    return PreservedAnalyses::all();
  }

  static bool isRequired() { return true; }
};

} // anonymous namespace

llvm::PassPluginLibraryInfo getDemoPrintPassPluginInfo() {
  return {LLVM_PLUGIN_API_VERSION, "DemoPrintPass", LLVM_VERSION_STRING,
          [](PassBuilder &PB) {
            PB.registerPipelineStartEPCallback(
                [](ModulePassManager &MPM, OptimizationLevel Level) {
                  MPM.addPass(
                      createModuleToFunctionPassAdaptor(DemoPrintPass()));
                });
          }};
}

extern "C" LLVM_ATTRIBUTE_WEAK ::llvm::PassPluginLibraryInfo
llvmGetPassPluginInfo() {
  return getDemoPrintPassPluginInfo();
}
